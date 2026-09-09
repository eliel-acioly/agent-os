#!/usr/bin/env python3
"""
query_engine.py — Agent-OS RAG Layer (agnóstico a projeto)
Motor de busca sobre o codebase do PROJETO LINKADO indexado no ChromaDB.
Uso: python .agents/rag/query_engine.py --query "como funciona o checkout" --agent API
     python .agents/rag/query_engine.py --query "YOLO detection pipeline" --top 5
"""

import sys
import os
import json
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_context import (
    get_project_root, get_agents_dir, get_project_slug,
    get_index_dir, legacy_index_dir, collection_name, legacy_collection_name,
)

# Feature flag com rollback: AGENTOS_HYBRID=0 restaura o caminho legado (keyword-first).
HYBRID_ENABLED = os.environ.get("AGENTOS_HYBRID", "1") != "0"

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
    ground_terms = [t.lower() for t in re.findall(r"[A-Za-z]{4,}", query)]

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
                        # Grounding anti-deriva: exige ≥1 termo da query no path ou no texto.
                        # Similaridade pura sem ancoragem lexical promove docs irrelevantes.
                        hay = f"{source}\n{(doc or '')[:800]}".lower()
                        if ground_terms and not any(t in hay for t in ground_terms):
                            continue
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
                            "relevance": relevance,
                            "_distance": distance,
                            "_collection": coll_name,
                            "_origin": "vector",
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
            r["_raw"] = r.pop("_score")
            r["_origin"] = "lexical"

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


# ---------------------------------------------------------------------------
# Agent-OS 2.0 — Retrieval Router + Hybrid Fusion (Agentic Retrieval)
# ---------------------------------------------------------------------------
INTENT_PATTERNS = [
    ("IMPACT_ANALYSIS", re.compile(r"o que quebra|se (eu )?(alterar|mudar|modificar|mexer)|impacto|depende de|quem usa|quem chama|what breaks|impact of|dependents", re.I)),
    ("EXPERIENCE_QUERY", re.compile(r"j[aá] (tivemos|teve|aconteceu|vimos)|problema anterior|como resolv|da outra vez|previous|last time", re.I)),
    ("HISTORICAL", re.compile(r"por ?que (foi|é|e) implementado|hist[oó]rico|quem (mudou|criou|alterou)|why was|\badr\b", re.I)),
    ("ENTITY_LOOKUP", re.compile(r"onde (est[aá]|fica|[eé] implementado)|where is|find (the )?(file|symbol|component)", re.I)),
    ("ARCHITECTURAL", re.compile(r"como funciona|arquitetura|fluxo de|end to end|how does|data flow", re.I)),
]

INTENT_MECHANISMS = {
    "ENTITY_LOOKUP":  ["symbols", "lexical"],
    "IMPACT_ANALYSIS": ["symbols", "graph", "lexical"],
    "EXPERIENCE_QUERY": ["memory", "lexical"],
    "HISTORICAL":     ["git", "lexical"],
    "ARCHITECTURAL":  ["vector", "lexical", "graph"],
    "CODE_SEARCH":    ["lexical", "vector", "symbols"],
}


def route_query(query: str) -> dict:
    """Classifica a intenção e devolve o plano de retrieval (mecanismos + orçamento)."""
    q = query.strip()
    # Lookup determinístico: path com extensão ou token CamelCase único
    if re.search(r"[\w\-/]+\.(tsx?|py|go|md|sql)\b", q) or re.match(r"^[A-Z][A-Za-z0-9_]+$", q):
        intent = "ENTITY_LOOKUP"
    else:
        intent = "CODE_SEARCH"
        for name, rx in INTENT_PATTERNS:
            if rx.search(q):
                intent = name
                break
    return {"intent": intent, "mechanisms": INTENT_MECHANISMS[intent], "query": q}


def symbol_candidates(query: str, top_k: int = 5, strong_only: bool = False) -> list:
    """Candidatos determinísticos do Code Knowledge Graph (score 1.0 exato)."""
    try:
        from code_graph import lookup
    except Exception:
        return []
    terms = re.findall(r"[A-Za-z_][A-Za-z0-9_/.\-]*", query)
    # Prioriza tokens com cara de entidade: CamelCase, paths, SNAKE_UPPER
    entities = [t for t in terms if re.match(r"^[A-Z][A-Za-z0-9]+$", t) or "/" in t or re.match(r"^[A-Z_]{4,}$", t)]
    if not entities:
        entities = [t for t in terms if len(t) >= 5][:2]
    out, seen = [], set()
    for ent in entities[:3]:
        try:
            for r in lookup(ent, limit=top_k):
                key = (r["file"], r["line"])
                if key in seen:
                    continue
                seen.add(key)
                exact = 1.0 if r["name"].lower() == ent.lower() or ent.lower() in r["file"].lower() else 0.6
                if strong_only and exact < 1.0:
                    continue  # CODE_SEARCH: só match forte; fracos poluem a fusão
                out.append({
                    "text": f"[{r['kind']}] {r['name']} — {r['file']}:{r['line']}",
                    "source": r["file"],
                    "start_line": r["line"],
                    "end_line": r["line"],
                    "file_type": "Symbol",
                    "_raw": exact,
                    "_origin": "symbols",
                })
        except Exception:
            continue
    return out[:top_k]


def graph_candidates(query: str, top_k: int = 5) -> list:
    """Vizinhança estrutural: callers dos arquivos-símbolo encontrados."""
    cands = symbol_candidates(query, top_k=3)
    if not cands:
        return []
    try:
        from code_graph import callers_of
    except Exception:
        return []
    out, seen = [], set()
    for c in cands:
        try:
            for r in callers_of(c["source"], limit=top_k):
                if r["file"] in seen:
                    continue
                seen.add(r["file"])
                out.append({
                    "text": f"Referenciado via {r['via']}: {r['file']}",
                    "source": r["file"],
                    "start_line": 0,
                    "end_line": 0,
                    "file_type": "Graph",
                    "_raw": 0.7,
                    "_origin": "graph",
                })
        except Exception:
            continue
    return out[:top_k]


def memory_candidates(query: str, agent: str = "Master", top_k: int = 3) -> list:
    """Experiências procedurais do projeto (Agentic Memory)."""
    try:
        sys.path.insert(0, str(AGENTS_DIR / "scripts"))
        from memory_consolidate import retrieve
        hits = retrieve(query, agent, top_k)
        return [{
            "text": h.get("lesson", "")[:400],
            "source": f"memory:experience:{h.get('id', '?')}",
            "start_line": 0, "end_line": 0,
            "file_type": "Experience",
            "_raw": float(h.get("utility", 0.5)),
            "_origin": "memory",
        } for h in hits]
    except Exception:
        return []


def git_candidates(query: str, top_k: int = 3) -> list:
    """Histórico recente de arquivos relacionados (Git graph leve)."""
    import subprocess
    cands = symbol_candidates(query, top_k=3)
    files = [c["source"] for c in cands] or []
    out = []
    for f in files[:3]:
        try:
            res = subprocess.run(["git", "log", "--oneline", "-3", "--", f],
                                 cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=15,
                                 encoding="utf-8", errors="replace")
            if res.returncode == 0 and res.stdout.strip():
                out.append({
                    "text": f"Histórico de {f}:\n" + res.stdout.strip()[:400],
                    "source": f"git:{f}",
                    "start_line": 0, "end_line": 0,
                    "file_type": "History",
                    "_raw": 0.6,
                    "_origin": "git",
                })
        except Exception:
            continue
    return out[:top_k]


def _normalize_raw(values: list) -> list:
    """Compat: min-max para [0,1] (lista de floats)."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [1.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def fuse_candidates(lists: dict, query: str, top_k: int = 5) -> list:
    """Fusão híbrida RRF + ponderada com proveniência por resultado."""
    weights = {"lexical": 0.42, "vector": 0.32, "symbols": 0.15, "graph": 0.05, "memory": 0.03, "git": 0.02}
    # Normaliza cada lista pelo seu bruto
    normed = {}
    for origin, items in lists.items():
        raws = []
        for it in items:
            if "_raw" in it:
                raws.append(float(it["_raw"]))
            elif "_score" in it:
                raws.append(float(it["_score"]))
            elif "_distance" in it:
                raws.append(max(0.0, 1.0 - float(it["_distance"]) / 2.0))
            else:
                raws.append(float(it.get("relevance", 0.5)))
        normed[origin] = _normalize_raw(raws)
    fused: dict = {}
    q_lower = query.lower()
    for origin, items in lists.items():
        w = weights.get(origin, 0.1)
        for rank, (it, n) in enumerate(zip(items, normed[origin])):
            key = (it.get("source", "?"), it.get("start_line", 0), it.get("end_line", 0))
            # Bônus: match exato de entidade no path + origem do projeto (não legado)
            bonus = 0.0
            src_lower = (it.get("source") or "").lower()
            for tok in re.findall(r"[A-Za-z]{5,}", query):
                if tok.lower() in src_lower:
                    bonus += 0.04
            if not src_lower.startswith(("memory:", "git:")) and origin in ("lexical", "vector", "symbols"):
                bonus += 0.05
            # Penalidade anti-ruído: harness de teste/bench e scripts internos raramente
            # são a resposta para consultas de código; docs puramente vetoriais também não.
            if "retrieval_bench" in src_lower or "test-" in src_lower or "/test_" in src_lower:
                bonus -= 0.20
            if src_lower.startswith(".agents/scripts/") and origin == "vector":
                bonus -= 0.15
            if src_lower.endswith(".md") and origin == "vector":
                bonus -= 0.10
            rrf = 1.0 / (60 + rank)
            contrib = w * n + 0.5 * rrf + bonus
            if key not in fused:
                fused[key] = {"item": dict(it), "score": 0.0, "origins": [], "parts": {}}
            fused[key]["score"] += contrib
            if origin not in fused[key]["origins"]:
                fused[key]["origins"].append(origin)
            fused[key]["parts"][origin] = round(n, 3)
    ranked = sorted(fused.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    results = []
    for r in ranked:
        it = r["item"]
        for k in ("_raw", "_score", "_distance", "_collection"):
            it.pop(k, None)
        it["relevance"] = round(min(0.98, 0.30 + r["score"] * 0.55), 3)
        it["confidence"] = it["relevance"]
        it["retrieval_source"] = r["origins"]
        it["provenance"] = f"fused({'/'.join(r['origins'])}) score={round(r['score'],3)}"
        results.append(it)
    return results


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
        origins = r.get("retrieval_source")
        prov = f" [{','.join(origins)}]" if origins else ""
        text = r.get("text", "")[:300]  # Trunca para não explodir tokens

        lines.append(f"\n[{i}] {source}:L{start}-{end}  (relevância: {relevance:.2f}{prov})")
        lines.append(f"```")
        lines.append(text)
        lines.append("```")

    return "\n".join(lines)


def log_query(agent: str, query: str, results_count: int, intent: str = "", sources: list | None = None):
    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "project": PROJECT_SLUG,
        "project_root": str(PROJECT_ROOT),
        "agent": agent,
        "event": "rag_query",
        "query": query,
        "results_count": results_count,
        "intent": intent or "CODE_SEARCH",
        "mechanisms": sources or [],
        "hybrid": HYBRID_ENABLED,
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


def _query_rag_legacy(query: str, agent: str = "Master", top_k: int = 5) -> list:
    """Caminho legado (keyword-first). Preservado para rollback via AGENTOS_HYBRID=0."""
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

    for r in results:
        for k in [k for k in r if k.startswith("_")]:
            r.pop(k, None)
    return results


def query_rag(query: str, agent: str = "Master", top_k: int = 5) -> list:
    """
    Interface principal — Agent-OS 2.0 Hybrid Retrieval (por projeto).

    Roteia a intenção (lexical? semântico? estrutural? experiência?) e funde
    candidatos com rerank + proveniência. Com AGENTOS_HYBRID=0, usa o legado.
    """
    plan = route_query(query)
    if not HYBRID_ENABLED:
        results = _query_rag_legacy(query, agent, top_k)
        log_query(agent, query, len(results), intent=plan["intent"], sources=["legacy"])
        return results

    mechs = plan["mechanisms"]
    lists: dict = {}
    if "lexical" in mechs:
        try:
            lex = search_sqlite_rag(query, top_k * 2)
            if lex:
                lists["lexical"] = lex
        except Exception:
            pass
    if "vector" in mechs:
        targets = AGENT_TARGETS.get(agent, ["all"])
        collection_names: list = []
        for t in targets:
            for c in _collections_for(agent, t):
                if c not in collection_names:
                    collection_names.append(c)
        try:
            vec = search_chromadb(query, collection_names, top_k * 2)
            if vec:
                lists["vector"] = vec
        except Exception:
            pass
    if "symbols" in mechs:
        sym = symbol_candidates(query, top_k, strong_only=(plan["intent"] != "ENTITY_LOOKUP"))
        if sym:
            lists["symbols"] = sym
    if "graph" in mechs:
        g = graph_candidates(query, top_k)
        if g:
            lists["graph"] = g
    if "memory" in mechs:
        m = memory_candidates(query, agent, 3)
        if m:
            lists["memory"] = m
    if "git" in mechs:
        h = git_candidates(query, 3)
        if h:
            lists["git"] = h

    if not lists:
        results = fallback_keyword_search(query, top_k)
        log_query(agent, query, len(results), intent=plan["intent"], sources=["fallback"])
        return results

    results = fuse_candidates(lists, query, top_k)
    log_query(agent, query, len(results), intent=plan["intent"], sources=list(lists.keys()))
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
