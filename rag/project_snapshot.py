#!/usr/bin/env python3
"""
project_snapshot.py — Agent-OS (agnóstico a projeto)
Gera um briefing do estado atual do PROJETO LINKADO combinando:
  - snapshots por projeto (memory/projects/<slug>/)
  - ChromaDB RAG por projeto
  - knowledge_base.json (lições e padrões)

Uso: python .agents/rag/project_snapshot.py --agent API --query "alertas Socket.IO"
     python .agents/rag/project_snapshot.py --agent AI_Edge  (usa query automática do agente)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
try:
    from project_context import get_project_root, get_agents_dir, get_project_slug, get_project_memory_dir
    PROJECT_ROOT = get_project_root()
    AGENTS_DIR = get_agents_dir()
    PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
    MEMORY_DIR = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR)
    LEGACY_MEMORY_DIR = AGENTS_DIR / "memory"
except Exception:
    AGENTS_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = AGENTS_DIR.parent
    PROJECT_SLUG = "proj"
    MEMORY_DIR = AGENTS_DIR / "memory"
    LEGACY_MEMORY_DIR = MEMORY_DIR
KNOWLEDGE_BASE = (AGENTS_DIR / "memory" / "knowledge_base.json")
GRAPH_STATUS_FILE = MEMORY_DIR / "graph_last_updated.json"
LEGACY_GRAPH_STATUS_FILE = LEGACY_MEMORY_DIR / "graph_last_updated.json"

SEPARATOR = "═" * 65

# Query padrão por agente — foca no domínio de trabalho do agente
DEFAULT_QUERIES = {
    "Product":     "backlog epics business requirements product features",
    "Security":    "authentication RLS middleware sanitization tenant isolation",
    "DB":          "schema drizzle ORM migrations postgres tables",
    "Gateway":     "gRPC protobuf mediamtx RTSP streaming gateway",
    "Contracts":   "shared contracts DTOs interfaces TypeScript types",
    "API":         "server routes controllers socket.io endpoints",
    "AI_Edge":     "YOLO detection inference worker uncertainty evidential",
    "UI":          "React components dashboard hooks state management",
    "Logs":        "tests E2E jest assertions coverage",
    "Master":      "architecture overview codebase structure dependencies",
    "Orchestrator": "handoff pipeline workflow agents orchestration",
    "Deploy":      "docker CI/CD github actions railway supabase deploy",
}


def load_graph_status() -> dict:
    for p in (GRAPH_STATUS_FILE, LEGACY_GRAPH_STATUS_FILE):
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                if data:
                    return data
        except Exception:
            continue
    return {}


def load_project_snapshots() -> list:
    """Carrega snapshots do projeto atual com fallback legado (exceto fósseis de outro projeto)."""
    summaries = []
    seen_targets = set()
    for base in (MEMORY_DIR, LEGACY_MEMORY_DIR):
        try:
            if not base.is_dir():
                continue
            for snapshot in base.glob("snapshot_*.json"):
                # No fallback legado, ignora fósseis de outro projeto
                if base == LEGACY_MEMORY_DIR and ("snapshot_antecipia-api" in snapshot.name or "snapshot_antecipia-ui" in snapshot.name):
                    continue
                try:
                    data = json.loads(snapshot.read_text(encoding="utf-8"))
                except Exception:
                    continue
                target = data.get("target", snapshot.stem)
                if target in seen_targets:
                    continue
                seen_targets.add(target)
                summaries.append(data)
        except Exception:
            continue
    return summaries


def get_rag_context(query: str, agent: str, top_k: int = 4) -> list:
    """Busca contexto relevante no RAG ChromaDB."""
    try:
        # Importar query_engine do diretório irmão
        sys.path.insert(0, str(AGENTS_DIR / "rag"))
        from query_engine import query_rag
        return query_rag(query, agent, top_k)
    except Exception as e:
        return [{"text": f"RAG não disponível: {e}", "source": "N/A", "relevance": 0}]


def print_snapshot(agent: str, query: str, show_rag: bool = True):
    print(f"\n{SEPARATOR}")
    print(f"  Project Snapshot [{PROJECT_SLUG}] — @{agent}")
    print(f"  Root: {PROJECT_ROOT}")
    print(f"  Query: '{query}'")
    print(SEPARATOR)

    # 1. Status do code-review-graph
    graph_status = load_graph_status()
    print(f"\n📊 CODE-REVIEW-GRAPH STATUS")
    print("─" * 65)
    if graph_status:
        for target, info in graph_status.items():
            updated = info.get("last_updated", "nunca")[:19]
            head = info.get("last_head", "unknown")
            changes = info.get("changes_detected", 0)
            rebuilt = "✅" if info.get("rebuilt") else "📄 snapshot"
            print(f"  {rebuilt} {target}: HEAD={head} | {changes} mudanças | Atualizado: {updated}")
    else:
        print("  ⚠️  Grafo não atualizado. Execute: python .agents/scripts/update_graph.py")

    # 2. Snapshots de código
    snapshots = load_project_snapshots()
    if snapshots:
        print(f"\n📁 ESTRUTURA DO CODEBASE")
        print("─" * 65)
        for snap in snapshots:
            target = snap.get("target", "unknown")
            counts = snap.get("file_counts", {})
            total = sum(counts.values())
            print(f"  {target}: {total} arquivos "
                  f"(TS:{counts.get('.ts',0)+counts.get('.tsx',0)} "
                  f"| PY:{counts.get('.py',0)} "
                  f"| GO:{counts.get('.go',0)})")
            recent = snap.get("recent_changes", [])
            if recent:
                print(f"    🔄 Modificados: {', '.join(recent[:3])}")

    # 3. Contexto RAG
    if show_rag:
        print(f"\n🔍 CONTEXTO SEMÂNTICO RAG — '{query}'")
        print("─" * 65)
        rag_results = get_rag_context(query, agent, top_k=3)

        if rag_results and rag_results[0].get("relevance", 0) > 0:
            for i, r in enumerate(rag_results, 1):
                source = r.get("source", "unknown")
                relevance = r.get("relevance", 0)
                text_preview = r.get("text", "")[:200].replace("\n", " ")
                print(f"  [{i}] {source} (relevância: {relevance:.2f})")
                print(f"      {text_preview}...")
        else:
            print("  ℹ️  Índice RAG vazio. Execute: python .agents/rag/indexer.py --target all")

    print(f"\n{SEPARATOR}\n")


def main():
    parser = argparse.ArgumentParser(description="Gera snapshot semântico do projeto para contexto de agente.")
    parser.add_argument("--agent", "-a",
                        default="Master",
                        choices=list(DEFAULT_QUERIES.keys()),
                        help="Agente que está abrindo sessão")
    parser.add_argument("--query", "-q",
                        help="Query personalizada (usa default do agente se omitida)")
    parser.add_argument("--no-rag", action="store_true",
                        help="Pular consulta RAG (apenas status do grafo)")
    args = parser.parse_args()

    query = args.query or DEFAULT_QUERIES.get(args.agent, "codebase architecture")
    print_snapshot(args.agent, query, show_rag=not args.no_rag)


if __name__ == "__main__":
    main()
