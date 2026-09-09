#!/usr/bin/env python3
"""
session_open.py — Agent-OS (agnóstico a projeto)
Abre uma sessão de agente carregando:
  1. Memória persistente (knowledge_base.json compartilhada + sessão por projeto)
  2. Snapshot do projeto linkado (memory/projects/<slug>/)
  3. Contexto RAG do projeto linkado (ChromaDB por slug)
Uso: python .agents/scripts/session_open.py [--agent NOME] [--query "contexto específico"] [--no-rag]
"""

import sys
import json
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))
from project_context import get_project_root, get_agents_dir, get_project_slug, get_project_memory_dir

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
PROJECT_MEMORY_DIR = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR)
MEMORY_DIR = AGENTS_DIR / "memory"
KNOWLEDGE_BASE = MEMORY_DIR / "knowledge_base.json"
METRICS_FILE = MEMORY_DIR / "agent_metrics.json"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"
PROJECT_SESSION_LOG = PROJECT_MEMORY_DIR / "session_log.jsonl"
HANDOFF_FILE = PROJECT_ROOT / "HANDOFF.md"

SEPARATOR = "═" * 65

def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def print_header(agent_name: str):
    print(f"\n{SEPARATOR}")
    print(f"  Agent-OS — Sessão Iniciada (projeto: {PROJECT_SLUG})")
    print(f"  Agente Ativo: @{agent_name}")
    print(f"  Root: {PROJECT_ROOT}")
    print(f"  Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)

def print_learnings(agent_name: str, kb: dict):
    agents_data = kb.get("agents", {})
    agent_data = agents_data.get(agent_name, {})
    learnings = agent_data.get("learnings", [])
    patterns = agent_data.get("patterns", [])

    print(f"\n📚 MEMÓRIA PERSISTENTE — @{agent_name}")
    print("─" * 65)
    if learnings:
        print("  🔶 Lições Aprendidas (carregar antes de codificar):")
        for i, l in enumerate(learnings, 1):
            print(f"     {i}. {l}")
    else:
        print("  ℹ️  Nenhuma lição registrada ainda para este agente.")

    if patterns:
        print("\n  🔷 Padrões Aprovados:")
        for p in patterns:
            print(f"     • {p}")

def print_architecture_decisions(kb: dict):
    decisions = kb.get("architecture_decisions", [])
    if decisions:
        print("\n🏛️  DECISÕES ARQUITETURAIS VIGENTES")
        print("─" * 65)
        for d in decisions:
            print(f"  [{d.get('date','')}] {d.get('decision','')}")

def print_metrics(agent_name: str, metrics: dict):
    agent_m = metrics.get("agents", {}).get(agent_name, {})
    if not agent_m:
        return
    score = agent_m.get("skill_score", 100)
    completed = agent_m.get("tasks_completed", 0)
    blocked = agent_m.get("tasks_blocked", 0)
    bar = "█" * (score // 10) + "░" * (10 - score // 10)
    print(f"\n📊 PERFORMANCE — @{agent_name}")
    print("─" * 65)
    print(f"  Skill Score: [{bar}] {score}/100")
    print(f"  Tasks Concluídas: {completed}  |  Bloqueios: {blocked}")

def print_handoff_context():
    if not HANDOFF_FILE.exists():
        return
    content = HANDOFF_FILE.read_text(encoding="utf-8")
    lines = [l for l in content.splitlines() if l.strip()][:6]
    print(f"\n📋 HANDOFF.md ATUAL (resumo)")
    print("─" * 65)
    for line in lines:
        print(f"  {line}")

def write_session_log(agent_name: str, start_ts: float, tokens_estimate: int = 0):
    model = os.environ.get("AGENT_LLM_MODEL") or os.environ.get("LLM_MODEL") or "ide-llm"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "project": PROJECT_SLUG,
        "project_root": str(PROJECT_ROOT),
        "agent": agent_name,
        "event": "session_opened",
        "duration_ms": round((time.time() - start_ts) * 1000, 2),
        "model": model,
        "tokens_estimated": tokens_estimate,
        "decision": "context_loaded"
    }
    for log_path in (PROJECT_SESSION_LOG, SESSION_LOG):
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            continue

def print_rag_context(agent_name: str, query: str):
    """Exibe contexto RAG semântico do projeto."""
    try:
        rag_dir = AGENTS_DIR / "rag"
        sys.path.insert(0, str(rag_dir))
        from project_snapshot import print_snapshot
        print_snapshot(agent_name, query, show_rag=True)
    except Exception as e:
        print(f"\n  ℹ️  RAG Snapshot não disponível ({type(e).__name__})")
        print(f"     Execute: python .agents/rag/indexer.py --target all")

def main():
    parser = argparse.ArgumentParser(description="Abre sessão de agente com contexto de memória + RAG.")
    parser.add_argument("--agent", "-a", default="Master",
                        help="Nome do agente (ex: API, UI, Logs, Master)")
    parser.add_argument("--query", "-q", default=None,
                        help="Query semântica personalizada para o RAG (usa default do agente se omitida)")
    parser.add_argument("--no-rag", action="store_true",
                        help="Pular consulta RAG (mais rápido, sem contexto de código)")
    args = parser.parse_args()
    agent_name = args.agent.strip().replace("@", "")
    start_ts = time.time()

    kb = load_json(KNOWLEDGE_BASE)
    metrics = load_json(METRICS_FILE)

    print_header(agent_name)
    print_learnings(agent_name, kb)
    print_architecture_decisions(kb)
    print_metrics(agent_name, metrics)
    print_handoff_context()

    # Integração RAG + code-review-graph
    if not args.no_rag:
        print_rag_context(agent_name, args.query or "")

    print(f"\n{SEPARATOR}")
    print("  ✅ Contexto carregado. O agente está pronto para operar.")
    print(SEPARATOR + "\n")

    # Estimativa conservadora de tokens de contexto carregado (heurística ~4 chars/token)
    tokens_estimate = 0
    for _path in (KNOWLEDGE_BASE, METRICS_FILE):
        if _path.exists():
            tokens_estimate += _path.stat().st_size // 4
    write_session_log(agent_name, start_ts, tokens_estimate)

if __name__ == "__main__":
    main()
