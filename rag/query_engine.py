#!/usr/bin/env python3
"""
query_engine.py — AntecipIA Agent Platform v2.0 — RAG Layer
Motor de busca semântica sobre o codebase indexado no ChromaDB.
Uso: python .agents/rag/query_engine.py --query "como funciona o RiskBuilder" --agent API
     python .agents/rag/query_engine.py --query "YOLO detection pipeline" --top 5
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = Path(__file__).parent.parent
INDEX_DIR = AGENTS_DIR / "rag" / "knowledge" / "project_index"
SESSION_LOG = AGENTS_DIR / "memory" / "session_log.jsonl"

SEPARATOR = "═" * 65

# Mapeamento de agente → coleção mais relevante
AGENT_COLLECTIONS = {
    "API":         ["antecipia_antecipia-api", "antecipia_all"],
    "UI":          ["antecipia_antecipia-ui", "antecipia_all"],
    "DB":          ["antecipia_antecipia-api", "antecipia_all"],
    "Contracts":   ["antecipia_shared", "antecipia_all"],
    "AI_Edge":     ["antecipia_services", "antecipia_all"],
    "Gateway":     ["antecipia_services", "antecipia_all"],
    "Logs":        ["antecipia_all"],
    "Master":      ["antecipia_all"],
    "Orchestrator":["antecipia_all"],
    "Deploy":      ["antecipia_all"],
}


def get_chroma_client():
    try:
        import chromadb
        if not INDEX_DIR.exists():
            return None
        client = chromadb.PersistentClient(path=str(INDEX_DIR))
        return client
    except ImportError:
        return None


def search_chromadb(query: str, collection_names: list, top_k: int = 5) -> list:
    """Busca semântica no ChromaDB usando embeddings nativos."""
    client = get_chroma_client()
    if not client:
        return []

    results = []
    seen_sources = set()

    for coll_name in collection_names:
        try:
            collection = client.get_collection(coll_name)
            space = (collection.metadata or {}).get("hnsw:space", "l2")
            res = collection.query(
                query_texts=[query],
                n_results=min(top_k, collection.count())
            )
            if res and res.get("documents"):
                for i, doc in enumerate(res["documents"][0]):
                    meta = res["metadatas"][0][i] if res.get("metadatas") else {}
                    source = meta.get("source", "unknown")
                    if source not in seen_sources:
                        seen_sources.add(source)
                        distance = res["distances"][0][i] if res.get("distances") else 0.0
                        if space == "cosine":
                            relevance = round(max(0.0, 1.0 - distance / 2.0), 3)
                        elif space == "ip":
                            relevance = round(max(0.0, min(1.0, distance)), 3)
                        else:
                            relevance = round(1.0 / (1.0 + distance), 3)
                        if relevance < 0.25:
                            continue
                        results.append({
                            "text": doc,
                            "source": source,
                            "start_line": meta.get("start_line", 0),
                            "end_line": meta.get("end_line", 0),
                            "file_type": meta.get("file_type", ""),
                            "relevance": relevance
                        })
        except Exception:
            continue

    # Ordenar por relevância decrescente
    results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:top_k]


def fallback_keyword_search(query: str, top_k: int = 5) -> list:
    """
    Fallback de busca por palavras-chave quando o ChromaDB não está indexado.
    Busca diretamente nos snapshots JSON gerados pelo update_graph.py.
    """
    snapshot_dir = AGENTS_DIR / "memory"
    results = []
    keywords = query.lower().split()

    for snapshot_file in snapshot_dir.glob("snapshot_*.json"):
        try:
            data = json.loads(snapshot_file.read_text(encoding="utf-8"))
            # Busca nos arquivos recentes modificados
            for change in data.get("recent_changes", []):
                if any(kw in change.lower() for kw in keywords):
                    results.append({
                        "text": f"Arquivo modificado recentemente: {change}",
                        "source": change,
                        "relevance": 0.5
                    })
        except Exception:
            continue

    return results[:top_k]


def format_results(results: list, query: str) -> str:
    """Formata os resultados para exibição ao agente."""
    if not results:
        return "Nenhum resultado encontrado no índice RAG."

    lines = [f"🔍 RAG Context — Query: '{query}'", "─" * 65]
    for i, r in enumerate(results, 1):
        source = r.get("source", "unknown")
        start = r.get("start_line", 0)
        end = r.get("end_line", 0)
        relevance = r.get("relevance", 0)
        text = r.get("text", "")[:300]  # Trunca para não explodir tokens

        lines.append(f"\n[{i}] {source}:L{start}-{end}  (relevância: {relevance:.2f})")
        lines.append(f"```")
        lines.append(text)
        lines.append("```")

    return "\n".join(lines)


def log_query(agent: str, query: str, results_count: int):
    if SESSION_LOG.parent.exists():
        entry = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "agent": agent,
            "event": "rag_query",
            "query": query,
            "results_count": results_count
        }
        with open(SESSION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def query_rag(query: str, agent: str = "Master", top_k: int = 5) -> list:
    """
    Interface principal para consulta RAG.
    Retorna lista de resultados ordenados por relevância.
    """
    collection_names = AGENT_COLLECTIONS.get(agent, ["antecipia_all"])

    # Tentar ChromaDB primeiro
    results = search_chromadb(query, collection_names, top_k)

    # Fallback para busca por keyword se ChromaDB vazio
    if not results:
        results = fallback_keyword_search(query, top_k)

    log_query(agent, query, len(results))
    return results


def main():
    parser = argparse.ArgumentParser(description="Busca semântica RAG no codebase AntecipIA.")
    parser.add_argument("--query", "-q", required=True, help="Consulta semântica")
    parser.add_argument("--agent", "-a", default="Master",
                        choices=list(AGENT_COLLECTIONS.keys()),
                        help="Agente consultante (define coleções prioritárias)")
    parser.add_argument("--top", "-k", type=int, default=5, help="Número de resultados")
    parser.add_argument("--json", "-j", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    results = query_rag(args.query, args.agent, args.top)

    if args.json:
        print(json.dumps(results, ensure_ascii=False))
        return

    print(f"\n{SEPARATOR}")
    print(f"  🔍 AntecipIA RAG Query Engine")
    print(f"  Agente: @{args.agent}  |  Query: '{args.query}'")
    print(SEPARATOR)

    print(format_results(results, args.query))

    if not results:
        print("\n[DICA] Execute primeiro: python .agents/rag/indexer.py --target all")

    print(f"\n{SEPARATOR}\n")


if __name__ == "__main__":
    main()
