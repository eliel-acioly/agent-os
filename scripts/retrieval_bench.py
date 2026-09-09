#!/usr/bin/env python3
"""
retrieval_bench.py — Benchmark próprio do Agent-OS para o retrieval (por projeto).

Golden set: consultas reais com arquivos esperados verificados no repositório.
Métricas: Recall@K, MRR, cobertura por fonte de retrieval.
Uso:
  python .agents/scripts/retrieval_bench.py --baseline   (mede motor atual, salva baseline)
  python .agents/scripts/retrieval_bench.py --compare    (mede atual vs baseline salvo)
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "rag"))
from project_context import get_project_root, get_agents_dir, get_project_slug, get_project_memory_dir

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
BENCH_FILE = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR) / "retrieval_baseline.json"

# (query, agent, [arquivos esperados — match por substring no source])
GOLDEN = [
    ("ProductDetailModal desconto frete", "UI", ["ProductDetailModal.tsx"]),
    ("order state machine transicao status", "API", ["order-state-machine.ts"]),
    ("CheckoutModal pagamento", "UI", ["CheckoutModal.tsx"]),
    ("lib types Listing Order", "Contracts", ["lib/types.ts"]),
    ("MarketplaceView subcategory filtro", "UI", ["MarketplaceView.tsx"]),
    ("entregador assumir entrega delivery partner", "API", ["entregador/pedidos/page.tsx", "orders/route.ts"]),
    ("CustomerOrdersDrawer pedidos cliente", "UI", ["CustomerOrdersDrawer.tsx"]),
    ("mercadopago webhook pix status", "API", ["mercadopago/webhook/route.ts"]),
    ("listings subcategory filter api", "API", ["listings/route.ts"]),
    ("order messages chat pedido", "API", ["messages/route.ts"]),
]

SEP = "=" * 70


def run_engine():
    from query_engine import query_rag
    return query_rag


def measure(query_rag, top_k: int = 5) -> dict:
    per_query = []
    for query, agent, expected in GOLDEN:
        try:
            results = query_rag(query, agent, top_k)
        except Exception as e:
            results = []
            per_query.append({"query": query, "error": str(e), "mrr": 0.0, "recall": 0.0})
            continue
        sources = [r.get("source", "") for r in results]
        hits = [i for i, s in enumerate(sources)
                if any(exp.lower() in s.lower() for exp in expected)]
        rr = 1.0 / (hits[0] + 1) if hits else 0.0
        found = {exp for exp in expected
                 if any(exp.lower() in s.lower() for s in sources)}
        flat_sources = sorted({s for r in results for s in (r.get("retrieval_source") or [r.get("source", "?")])})
        per_query.append({
            "query": query, "agent": agent, "expected": expected,
            "top_sources": sources[:top_k],
            "retrieval_sources": flat_sources,
            "mrr": rr, "recall": len(found) / len(expected),
        })
    mrr = sum(q["mrr"] for q in per_query) / len(per_query)
    recall = sum(q["recall"] for q in per_query) / len(per_query)
    return {"mrr": round(mrr, 3), "recall_at_5": round(recall, 3),
            "n": len(per_query), "queries": per_query}


def main():
    p = argparse.ArgumentParser(description="Benchmark de retrieval do Agent-OS.")
    p.add_argument("--baseline", action="store_true", help="Mede e salva baseline")
    p.add_argument("--compare", action="store_true", help="Mede atual e compara com baseline")
    p.add_argument("--json", action="store_true")
    p.add_argument("--top", type=int, default=5)
    args = p.parse_args()

    query_rag = run_engine()
    current = measure(query_rag, args.top)
    current["timestamp"] = datetime.now().isoformat()
    current["project"] = PROJECT_SLUG

    if args.baseline or not BENCH_FILE.exists():
        BENCH_FILE.parent.mkdir(parents=True, exist_ok=True)
        BENCH_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{SEP}\n  BASELINE SALVO [{PROJECT_SLUG}] MRR={current['mrr']} Recall@5={current['recall_at_5']}\n{SEP}")
        if not args.json:
            for q in current["queries"]:
                print(f"  MRR={q['mrr']} R={q['recall']} :: {q['query'][:60]}")
        else:
            print(json.dumps(current, indent=2, ensure_ascii=False))
        return

    base = json.loads(BENCH_FILE.read_text(encoding="utf-8"))
    comp = {"baseline": {"mrr": base["mrr"], "recall_at_5": base["recall_at_5"]},
            "current": {"mrr": current["mrr"], "recall_at_5": current["recall_at_5"]},
            "delta_mrr": round(current["mrr"] - base["mrr"], 3),
            "delta_recall": round(current["recall_at_5"] - base["recall_at_5"], 3),
            "verdict": "PROMOTE" if (current["mrr"] >= base["mrr"] and current["recall_at_5"] >= base["recall_at_5"]) else "INVESTIGATE"}
    if args.json:
        print(json.dumps({"comparison": comp, "current": current}, indent=2, ensure_ascii=False))
    else:
        print(f"{SEP}\n  RETRIEVAL BENCH [{PROJECT_SLUG}]\n{SEP}")
        print(f"  Baseline: MRR={base['mrr']} Recall@5={base['recall_at_5']}")
        print(f"  Atual:    MRR={current['mrr']} Recall@5={current['recall_at_5']}")
        print(f"  Delta:    MRR={comp['delta_mrr']:+} Recall={comp['delta_recall']:+} => {comp['verdict']}")
        for q in current["queries"]:
            print(f"    MRR={q['mrr']} R={q['recall']} :: {q['query'][:60]}")
        print(SEP)


if __name__ == "__main__":
    main()
