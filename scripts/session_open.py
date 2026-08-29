#!/usr/bin/env python3
"""
session_open.py — AntecipIA Agent Platform v2.0
Abre uma sessão de agente carregando:
  1. Memória persistente (knowledge_base.json)
  2. Snapshot do code-review-graph (estado do projeto)
  3. Contexto RAG semântico relevante ao agente (ChromaDB)
Uso: python .agents/scripts/session_open.py [--agent NOME] [--query "contexto específico"] [--no-rag]
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

AGENTS_DIR = Path(__file__).parent.parent
MEMORY_DIR = AGENTS_DIR / "memory"
KNOWLEDGE_BASE = MEMORY_DIR / "knowledge_base.json"
METRICS_FILE = MEMORY_DIR / "agent_metrics.json"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"
HANDOFF_FILE = Path("HANDOFF.md")

SEPARATOR = "═" * 65

def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def print_header(agent_name: str):
    print(f"\n{SEPARATOR}")
    print(f"  🤖 AntecipIA Agent Platform v2.0 — Sessão Iniciada")
    print(f"  Agente Ativo: @{agent_name}")
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

def write_session_log(agent_name: str):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "event": "session_opened"
    }
    with open(SESSION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

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

    write_session_log(agent_name)

if __name__ == "__main__":
    main()
