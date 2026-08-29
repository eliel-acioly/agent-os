#!/usr/bin/env python3
"""
project_snapshot.py — AntecipIA Agent Platform v2.0 — RAG Layer
Gera um briefing semântico do estado atual do projeto combinando:
  - code-review-graph (estrutura arquitetural)
  - ChromaDB RAG (contexto semântico relevante)
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

AGENTS_DIR = Path(__file__).parent.parent
ROOT = AGENTS_DIR.parent
MEMORY_DIR = AGENTS_DIR / "memory"
KNOWLEDGE_BASE = MEMORY_DIR / "knowledge_base.json"
GRAPH_STATUS_FILE = MEMORY_DIR / "graph_last_updated.json"

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
    if GRAPH_STATUS_FILE.exists():
        return json.loads(GRAPH_STATUS_FILE.read_text(encoding="utf-8"))
    return {}


def load_project_snapshots() -> list:
    """Carrega snapshots estáticos gerados pelo update_graph.py."""
    summaries = []
    for snapshot in MEMORY_DIR.glob("snapshot_*.json"):
        try:
            data = json.loads(snapshot.read_text(encoding="utf-8"))
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
    print(f"  🗺️  Project Snapshot — @{agent}")
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
