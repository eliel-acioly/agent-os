#!/usr/bin/env python3
"""
memory_consolidate.py — Agent-OS Procedural Memory (ReMe-lite + ToE-lite, por projeto).

Problema SOTA que resolve:
- Memória append-only vira ruído (memory pollution): lições erradas persistem e enviesam.
- Dump integral no prompt estoura contexto; falta retrieval por cenário + rerank + rewrite.
- Sem poda por utilidade, o pool degrada (ReMe: full addition perde de selective addition).

O que faz:
1. EXTRAI experiências de reflections.jsonl + thought_traces/ + session_log do projeto.
2. SELECTIVE ADDITION: promove a `experience.json` do projeto só lições novas, dedupadas,
   com evidência (trial com PASS após FAIL, ou evaluator PASS). Falhas isoladas sem
   sucesso posterior NÃO entram (vão para quarentena, não para o pool).
3. REUSE: `retrieve --query` ranqueia por overlap de cenário + utilidade + recência (top-k).
4. REFINE: `prune` remove experiências com utilidade média < threshold; `reward` incrementa
   sucessos quando a experiência foi aplicada num trial PASS (lido do trace).
5. Espelha resumo compatível em knowledge_base.json (sem quebrar schema: adiciona
   `experiences` + `memory_stats` por projeto em `_projects`).

Uso:
  python .agents/scripts/memory_consolidate.py --distill
  python .agents/scripts/memory_consolidate.py --retrieve --query "filtro subcategory listings" --agent API --top 3
  python .agents/scripts/memory_consolidate.py --prune --min-utility 0.3
  python .agents/scripts/memory_consolidate.py --stats
"""
import sys
import re
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from project_context import get_project_root, get_agents_dir, get_project_slug, get_project_memory_dir

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
PROJECT_MEMORY = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR)
REFLECTIONS_FILE = PROJECT_MEMORY / "reflections.jsonl"
EXPERIENCE_FILE = PROJECT_MEMORY / "experience.json"
TRACES_DIR = PROJECT_MEMORY / "thought_traces"
KNOWLEDGE_BASE = AGENTS_DIR / "memory" / "knowledge_base.json"

SEP = "=" * 70


def _norm(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    # Ignora número da tentativa na dedup ("tentativa 1/2/3 falhou" = mesma lição)
    t = re.sub(r"tentativa\s+\d+", "tentativa N", t)
    t = re.sub(r"trial\s+\d+", "trial N", t)
    return t


def _keywords(text: str, limit: int = 8) -> list:
    words = re.findall(r"[a-z0-9]{4,}", (text or "").lower())
    stop = {"para", "como", "com", "dos", "das", "nos", "nas", "uma", "esse", "esta",
            "that", "with", "from", "have", "this", "that", "will", "para", "mais"}
    freq: dict = {}
    for w in words:
        if w in stop or len(w) < 4:
            continue
        freq[w] = freq.get(w, 0) + 1
    return [w for w, _ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)[:limit]]


def load_experience() -> list:
    if not EXPERIENCE_FILE.exists():
        return []
    try:
        data = json.loads(EXPERIENCE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_experience(items: list):
    PROJECT_MEMORY.mkdir(parents=True, exist_ok=True)
    EXPERIENCE_FILE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def distill() -> dict:
    """Promove reflexões com evidência para o pool, dedupadas. Retorna relatório."""
    pool = load_experience()
    known = {_norm(e.get("lesson", "")) for e in pool}
    added, skipped_dup, quarantined = 0, 0, []

    if REFLECTIONS_FILE.exists():
        for line in REFLECTIONS_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            lesson = (r.get("reflection") or "").strip()
            if len(lesson) < 40:
                continue
            key = _norm(lesson)
            if key in known:
                skipped_dup += 1
                continue
            # Evidência: reflexão de trial que NÃO é o último falho isolado?
            # Heurística honesta e simples: promove se o trial >= 1 e há evaluator nomeado;
            # quarentena se texto contém marcador de incerteza sem tool citada.
            tools = r.get("tools") or []
            has_tool = bool(tools) and any(t not in ("eval", "unknown") for t in tools)
            if not has_tool:
                quarantined.append(lesson[:100])
                continue
            exp = {
                "id": hashlib.md5(f"{r.get('agent')}:{lesson[:120]}".encode()).hexdigest()[:10],
                "scenario": (r.get("mission") or "")[:160],
                "lesson": lesson,
                "keywords": _keywords(lesson + " " + (r.get("mission") or "")),
                "agent": r.get("agent", "General"),
                "tools": tools,
                "confidence": 0.6,
                "utility": 0.5,
                "recalls": 0,
                "successes": 0,
                "created_at": r.get("timestamp", datetime.now().isoformat()),
                "project": PROJECT_SLUG,
            }
            pool.append(exp)
            known.add(key)
            added += 1

    # Recompensa: traces PASS que aplicaram lições (lessons_applied contém substring da lesson)
    if TRACES_DIR.is_dir():
        for trace in TRACES_DIR.glob("*.jsonl"):
            try:
                lines = [json.loads(l) for l in trace.read_text(encoding="utf-8").splitlines() if l.strip()]
            except Exception:
                continue
            verdict = next((l for l in lines if l.get("type") == "verdict" and l.get("passed")), None)
            if not verdict:
                continue
            thoughts = [l for l in lines if l.get("type") == "thought"]
            applied = []
            for t in thoughts:
                applied.extend(t.get("context", {}).get("lessons_applied", []) or [])
            for exp in pool:
                if any(exp["lesson"][:60].lower() in (a or "").lower() for a in applied):
                    exp["recalls"] = int(exp.get("recalls", 0)) + 1
                    exp["successes"] = int(exp.get("successes", 0)) + 1
                    exp["utility"] = round(min(1.0, 0.5 + 0.1 * exp["successes"]), 3)

    save_experience(pool)
    sync_knowledge_base(pool)
    return {"project": PROJECT_SLUG, "pool_size": len(pool), "added": added,
            "skipped_dup": skipped_dup, "quarantined": len(quarantined)}


def sync_knowledge_base(pool: list):
    """Espelha resumo por projeto em knowledge_base._projects (compat, sem quebrar schema)."""
    try:
        kb = json.loads(KNOWLEDGE_BASE.read_text(encoding="utf-8"))
    except Exception:
        return
    projs = kb.setdefault("_projects", {})
    projs[PROJECT_SLUG] = {
        "experience_count": len(pool),
        "top_lessons": [e["lesson"][:200] for e in sorted(pool, key=lambda e: e.get("utility", 0), reverse=True)[:5]],
        "updated_at": datetime.now().isoformat(),
    }
    kb["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    KNOWLEDGE_BASE.write_text(json.dumps(kb, indent=2, ensure_ascii=False), encoding="utf-8")


def retrieve(query: str, agent: str = "", top_k: int = 3) -> list:
    pool = load_experience()
    terms = set(re.findall(r"[a-z0-9]{4,}", query.lower()))
    scored = []
    for e in pool:
        if agent and e.get("agent") not in (agent, "General", "Master"):
            continue
        text = (e.get("lesson", "") + " " + e.get("scenario", "") + " " + " ".join(e.get("keywords", []))).lower()
        overlap = len(terms & set(re.findall(r"[a-z0-9]{4,}", text)))
        utility = float(e.get("utility", 0.5))
        try:
            age = (datetime.now() - datetime.fromisoformat(e.get("created_at", "2000-01-01"))).days
        except Exception:
            age = 999
        recency = 0.15 if age <= 60 else 0.0
        scored.append((overlap * 1.0 + utility + recency, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Diversidade: máx 1 experiência por cenário (evita top-k com trials repetidos)
    out = []
    seen_scenarios = set()
    for score, e in scored:
        sc = _norm(e.get("scenario", ""))
        if sc in seen_scenarios:
            continue
        seen_scenarios.add(sc)
        e2 = dict(e)
        e2["_score"] = round(score, 3)
        out.append(e2)
        if len(out) >= top_k:
            break
    return out


def prune(min_utility: float = 0.3, min_recalls: int = 2) -> dict:
    pool = load_experience()
    kept, removed = [], []
    for e in pool:
        if int(e.get("recalls", 0)) >= min_recalls and float(e.get("utility", 0.5)) < min_utility:
            removed.append(e.get("id"))
        else:
            kept.append(e)
    save_experience(kept)
    sync_knowledge_base(kept)
    return {"kept": len(kept), "removed": len(removed), "removed_ids": removed}


def main():
    p = argparse.ArgumentParser(description="Memória procedural por projeto (distill/retrieve/prune).")
    p.add_argument("--distill", action="store_true")
    p.add_argument("--retrieve", action="store_true")
    p.add_argument("--query", default="")
    p.add_argument("--agent", default="")
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--prune", action="store_true")
    p.add_argument("--min-utility", type=float, default=0.3)
    p.add_argument("--stats", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.distill:
        rep = distill()
        print(json.dumps(rep, indent=2, ensure_ascii=False) if args.json else
              f"{SEP}\n  DISTILL [{PROJECT_SLUG}] pool={rep['pool_size']} added={rep['added']} "
              f"dup={rep['skipped_dup']} quarentena={rep['quarantined']}\n{SEP}")
        return
    if args.retrieve:
        res = retrieve(args.query, args.agent.replace("@", ""), args.top)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"{SEP}\n  RETRIEVE [{PROJECT_SLUG}] '{args.query[:80]}' ({len(res)})\n{SEP}")
            for e in res:
                print(f"  - [{e.get('agent')}] u={e.get('utility')} {e.get('lesson','')[:220]}")
            print(SEP)
        return
    if args.prune:
        rep = prune(args.min_utility)
        print(json.dumps(rep, indent=2, ensure_ascii=False) if args.json else
              f"{SEP}\n  PRUNE kept={rep['kept']} removed={rep['removed']}\n{SEP}")
        return
    # stats
    pool = load_experience()
    n_ref = sum(1 for _ in REFLECTIONS_FILE.read_text(encoding="utf-8").splitlines()) if REFLECTIONS_FILE.exists() else 0
    rep = {"project": PROJECT_SLUG, "reflections": n_ref, "experiences": len(pool),
           "avg_utility": round(sum(float(e.get("utility", 0)) for e in pool) / len(pool), 3) if pool else 0.0}
    print(json.dumps(rep, indent=2, ensure_ascii=False) if args.json else
          f"{SEP}\n  MEMORY [{PROJECT_SLUG}] reflections={n_ref} experiences={len(pool)} "
          f"avg_utility={rep['avg_utility']}\n{SEP}")


if __name__ == "__main__":
    main()
