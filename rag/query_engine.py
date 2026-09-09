#!/usr/bin/env python3
"""
query_engine.py — Agent-OS RAG Layer (agnóstico a projeto)
Motor de busca sobre o codebase do PROJETO LINKADO indexado no ChromaDB.
Uso: python .agents/rag/query_engine.py --query "como funciona o checkout" --agent API
     python .agents/rag/query_engine.py --query "YOLO detection pipeline" --top 5
"""

import sys
import json
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_context import (
    get_project_root, get_agents_dir, get_project_slug,
    get_index_dir, legacy_index_dir, collection_name, legacy_collection_name,
)

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
INDEX_DIR = get_index_dir(PROJECT_ROOT, AGENTS_DIR)
LEGACY_INDEX_DIR = legacy_index_dir(AGENTS_DIR)
SESSION_LOG = AGENTS_DIR / "memory" / "session_log.jsonl"
PROJECT_SESSION_LOG = AGENTS_DIR / "memory" / "projects" / PROJECT_SLUG / "session_log.jsonl"

SEPARATOR = "═" * 65


def _collections_for(agent: str, target_hint: str = "all") -> list:
    """Coleções por projeto com fallback legado antecipia_* para migração."""
    primary = collection_name(target_hint, PROJECT_ROOT)
    legacy = legacy_collection_name(target_hint)
    # Ordem: projeto primeiro, legado como fallback
    return [primary] if primary == legacy else [primary, legacy]


# Mapeamento de agente → alvos (targets do indexer), resolvidos por projeto
AGENT_TARGETS = {
    "API":         ["app", "lib", "all"],
    "UI":          ["components", "app", "all"],
    "DB":          ["lib", "app", "all"],
    "Contracts":   ["lib", "all"],
    "AI_Edge":     ["lib", "all"],
    "Gateway":     ["lib", "all"],
    "Logs":        ["all"],
    "Master":      ["all"],
    "Orchestrator":["all"],
    "Deploy":      ["all"],
}

# Alias de compat: callers antigos esperam AGENT_COLLECTIONS com nomes prontos.
# Construído dinamicamente por projeto (com fallback legado na busca).
AGENT_COLLECTIONS = {
    agent: [c for t in targets for c in _collections_for(agent, t)]
    for agent, targets in AGENT_TARGETS.items()
}


def get_chroma_client_for(index_path: Path):
    try:
        import chromadb
        if not index_path.exists():
            return None
        return chromadb.PersistentClient(path=str(index_path))
    except ImportError:
        return None


def get_chroma_client():
    # Projeto primeiro, legado como fallback
    client = get_chroma_client_for(INDEX_DIR)
    if client is not None:
        return client
    if LEGACY_INDEX_DIR != INDEX_DIR:
        return get_chroma_client_for(LEGACY_INDEX_DIR)
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


def _search_sqlite_file(db_file: Path, query: str, top_k: int) -> list:
    """Busca keyword ranqueada em um chroma.sqlite3 específico."""
    if not db_file.exists():
        return []
    import sqlite3
    try:
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()

        terms = [t.lower() for t in query.split() if len(t) > 1]
        if not terms:
            return []

        sql = '''
        SELECT 
            e.id,
            MAX(CASE WHEN m.key = 'source' THEN m.string_value END) as source,
            MAX(CASE WHEN m.key = 'start_line' THEN m.int_value END) as start_line,
            MAX(CASE WHEN m.key = 'end_line' THEN m.int_value END) as end_line,
            MAX(CASE WHEN m.key = 'file_type' THEN m.string_value END) as file_type,
            MAX(CASE WHEN m.key = 'chroma:document' THEN m.string_value END) as document
        FROM embeddings e
        JOIN embedding_metadata m ON e.id = m.id
        GROUP BY e.id
        '''

        cur.execute(sql)
        rows = cur.fetchall()

        results = []
        for row in rows:
            eid, source, start_l, end_l, file_type, doc = row
            if not doc:
                continue

            doc_lower = doc.lower()
            source_lower = (source or '').lower()
            combined = doc_lower + ' ' + source_lower

            score = 0
            if query.lower() in combined:
                score += 5.0
            for term in terms:
                if term in source_lower:
                    score += 2.5
                matches = doc_lower.count(term)
                score += min(matches, 5) * 0.8

            if score > 0:
                relevance = round(min(0.98, 0.45 + (score * 0.08)), 2)
                results.append({
                    "text": doc,
                    "source": source or "unknown",
                    "start_line": start_l or 0,
                    "end_line": end_l or 0,
                    "file_type": file_type or "",
                    "relevance": relevance,
                    "_score": score
                })

        results.sort(key=lambda x: x["_score"], reverse=True)
        for r in results:
            del r["_score"]

        return results[:top_k]
    except Exception:
        return []


def search_sqlite_rag(query: str, top_k: int = 5) -> list:
    """Busca híbrida no SQLite do RAG: projeto primeiro, legado como fallback."""
    results = _search_sqlite_file(INDEX_DIR / "chroma.sqlite3", query, top_k)
    if results:
        return results
    if LEGACY_INDEX_DIR != INDEX_DIR:
        return _search_sqlite_file(LEGACY_INDEX_DIR / "chroma.sqlite3", query, top_k)
    return []


def fallback_keyword_search(query: str, top_k: int = 5) -> list:
    """
    Fallback por palavras-chave nos snapshots do PROJETO atual
    (memory/projects/<slug>/) com fallback para memory/ legado.
    """
    results = []
    keywords = query.lower().split()

    snapshot_dirs = []
    proj_mem = AGENTS_DIR / "memory" / "projects" / PROJECT_SLUG
    if proj_mem.is_dir():
        snapshot_dirs.append(proj_mem)
    snapshot_dirs.append(AGENTS_DIR / "memory")

    seen = set()
    for snapshot_dir in snapshot_dirs:
        for snapshot_file in snapshot_dir.glob("snapshot_*.json"):
            # Ignora snapshots fósseis de outro projeto no fallback legado
            if snapshot_dir == AGENTS_DIR / "memory" and "antecipia-api" in snapshot_file.name:
                continue
            if snapshot_dir == AGENTS_DIR / "memory" and "antecipia-ui" in snapshot_file.name:
                continue
            try:
                data = json.loads(snapshot_file.read_text(encoding="utf-8"))
                for change in data.get("recent_changes", []):
                    if change in seen:
                        continue
                    if any(kw in change.lower() for kw in keywords):
                        seen.add(change)
                        results.append({
                            "text": f"Arquivo modificado recentemente: {change}",
                            "source": change,
                            "relevance": 0.5
                        })
                        if len(results) >= top_k:
                            return results
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
    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "project": PROJECT_SLUG,
        "project_root": str(PROJECT_ROOT),
        "agent": agent,
        "event": "rag_query",
        "query": query,
        "results_count": results_count
    }
    # Log por projeto (novo) + log global (compat)
    for log_path in (PROJECT_SESSION_LOG, SESSION_LOG):
        try:
            if log_path.parent.exists() or log_path == SESSION_LOG:
                if log_path == PROJECT_SESSION_LOG:
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            continue


def query_rag(query: str, agent: str = "Master", top_k: int = 5) -> list:
    """
    Interface principal para consulta RAG (por projeto).
    Retorna lista de resultados ordenados por relevância.
    """
    targets = AGENT_TARGETS.get(agent, ["all"])
    collection_names: list = []
    for t in targets:
        for c in _collections_for(agent, t):
            if c not in collection_names:
                collection_names.append(c)

    # CAMADA 1 (PRIMÁRIA): busca híbrida SQLite — determinística, rápida e sem dependência
    # de bibliotecas nativas (hnswlib). Resiliente por design (ADR-009).
    results = search_sqlite_rag(query, top_k)

    # CAMADA 2 (REFORÇO OPCIONAL): ChromaDB vetorial quando o índice HNSW está saudável.
    # Enriquece com achados semânticos de outras fontes, sem substituir o primário.
    if results:
        seen_sources = {r.get("source") for r in results}
        try:
            vector_hits = search_chromadb(query, collection_names, top_k)
        except Exception:
            vector_hits = []
        for hit in vector_hits:
            src = hit.get("source")
            if src not in seen_sources:
                results.append(hit)
                seen_sources.add(src)
        results = results[:top_k]

    # CAMADA 3 (FALLBACK): snapshots de arquivos modificados recentemente
    if not results:
        results = fallback_keyword_search(query, top_k)

    log_query(agent, query, len(results))
    return results


def main():
    parser = argparse.ArgumentParser(description="Busca RAG no codebase do projeto linkado.")
    parser.add_argument("--query", "-q", required=True, help="Consulta semântica")
    parser.add_argument("--agent", "-a", default="Master",
                        choices=list(AGENT_TARGETS.keys()),
                        help="Agente consultante (define coleções prioritárias)")
    parser.add_argument("--top", "-k", type=int, default=5, help="Número de resultados")
    parser.add_argument("--json", "-j", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    results = query_rag(args.query, args.agent, args.top)

    if args.json:
        print(json.dumps(results, ensure_ascii=False))
        return

    print(f"\n{SEPARATOR}")
    print(f"  RAG Query Engine (projeto: {PROJECT_SLUG})")
    print(f"  Agente: @{args.agent}  |  Query: '{args.query}'")
    print(SEPARATOR)

    print(format_results(results, args.query))

    if not results:
        print("\n[DICA] Execute primeiro: python .agents/rag/indexer.py --target all")

    print(f"\n{SEPARATOR}\n")


if __name__ == "__main__":
    main()
