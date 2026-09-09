#!/usr/bin/env python3
"""
model_router.py — Roteamento Inteligente de Modelos + Ledger de Custos (agnóstico a projeto).
Classifica tarefas por complexidade e recomenda o modelo mais econômico-certo, registrando
cada decisão + estimativa de custo em .agents/memory/cost_ledger.jsonl.

Tiers (calibrados com mercado 2026 — Claude Code/Codex/Cursor/Devin):
  economy  -> reflexões, resumos, QA leve, rewrites (ex: GPT-5.6 Luna -80% 30jul26,
              Cursor Composer 2.5 ~1/10 do frontier, Haiku/Flash).   ~$0.20/M in,  $1.00/M out
  standard -> UI/API/debug cirúrgico, planos ReAct (ex: Sonnet 5 default 1M ctx,
              GPT-5.6 Terra -20%, Gemini 2.5 Pro).                    ~$2.50/M in, $12.00/M out
  premium  -> arquitetura, security, review adversarial, LATS (ex: Opus 4.7/4.8 líder
              SWE-bench Pro 64-69%, GPT-5.6 Sol recordista Terminal-Bench, Fable 5).
                                                                     ~$12.00/M in, $60.00/M out
Regra de uso no thinking loop: Thought/Act=standard, Reflect/consolidate=economy,
Critic/gate=premium. Fontes: benchmarks públicos mai-ago/2026 (SWE-bench Pro,
Terminal-Bench 2.1) — revalidar trimestralmente, Verified está saturado/contaminado.

Uso:
  python .agents/scripts/model_router.py --analyze "Implementar filtro de subcategorias com paginação"
  python .agents/scripts/model_router.py --log --agent API --task "fix checkout" --tokens 4000 --output 800
  python .agents/scripts/model_router.py --ledger
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
try:
    from project_context import get_project_root, get_agents_dir
    PROJECT_ROOT = get_project_root()
    AGENTS_DIR = get_agents_dir()
except Exception:
    AGENTS_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = Path.cwd()

ROOT = PROJECT_ROOT
MEMORY_DIR = AGENTS_DIR / "memory"
COST_LEDGER = MEMORY_DIR / "cost_ledger.jsonl"
SEP = "=" * 70

MODEL_HINT = {
    "economy":  ["gpt-5.6-luna", "composer-2.5", "claude-haiku", "gemini-flash"],
    "standard": ["claude-sonnet-5", "gpt-5.6-terra", "gemini-2.5-pro"],
    "premium":  ["claude-opus-4.8", "gpt-5.6-sol", "claude-fable-5"],
}

PRICING = {  # USD por 1M tokens (estimativas 2026, revalidar trimestralmente)
    "economy":  {"input": 0.20, "output": 1.00},
    "standard": {"input": 2.50, "output": 12.00},
    "premium":  {"input": 12.00, "output": 60.00},
}

# Palavras que elevam a complexidade (PT/EN, substring)
HIGH_SIGNAL = ["arquitetura", "architecture", "migration", "schema", "rls", "security",
               "adversarial", "review", "estrutural", "full-stack", "infra", "rate limit",
               "thread", "concorrência", "concurrency", "realtime", "webhook", "split", "pix",
               "fraude", "anti-fraude", "refactor amplo", "e2e", "lats", "mcts", "multi-agent"]
MID_SIGNAL = ["api", "rota", "route", "endpoint", "componente", "tela", "checkout", "pedido",
              "order", "listagem", "listing", "filtro", "filter", "pagina", "paging",
              "dashboard", "drawer", "auth", "login", "teste", "test", "debug", "otimiz",
              "refactor", "modal", "entreg", "deliver", "pagamento", "payment"]


def classify_complexity(mission: str) -> dict:
    low = mission.lower()
    score = 0
    for kw in HIGH_SIGNAL:
        if kw in low:
            score += 2
    for kw in MID_SIGNAL:
        if kw in low:
            score += 1
    score += min(len(mission) // 400, 3)  # missões longas = mais complexas
    if score >= 6:
        tier = "premium"
    elif score >= 3:
        tier = "standard"
    else:
        tier = "economy"
    return {
        "complexity_score": score,
        "tier": tier,
        "rationale": (
            f"{score} pontos de complexidade (alto impacto: "
            f"{sum(1 for kw in HIGH_SIGNAL if kw in low)}; longa: {len(mission)} chars)"
        ),
    }


def estimate_cost(tier: str, tokens_in: int, tokens_out: int) -> dict:
    p = PRICING[tier]
    total = (tokens_in / 1e6) * p["input"] + (tokens_out / 1e6) * p["output"]
    return {
        "tier": tier,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "estimated_cost_usd": round(total, 4),
        "model_suggested": MODEL_HINT[tier],
    }


def log_entry(entry: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(COST_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def show_ledger():
    if not COST_LEDGER.exists():
        print("  (ledger vazio)")
        return
    print(f"{SEP}\n  💰 LEDGER DE CUSTO/MODELO\n{SEP}")
    total = 0.0
    for line in COST_LEDGER.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        total += e.get("estimated_cost_usd", 0)
        print(f"  {e.get('timestamp','')[:19]}  @{e.get('agent','?'):<6} {e.get('tier','?'):<9} "
              f"{str(e.get('model_suggested',''))[:24]:<25} ≈ ${e.get('estimated_cost_usd',0):.4f}  {e.get('task','')[:30]}")
    print(f"\n  💵 Custo total estimado (ledger): ${total:.4f}")
    print(SEP + "\n")


def main():
    p = argparse.ArgumentParser(description="model_router — roteamento de modelos e ledger de custos.")
    p.add_argument("--analyze", "-a", metavar="MISSÃO", help="Classifica complexidade e recomenda modelo")
    p.add_argument("--log", action="store_true", help="Registra decisão/uso no ledger")
    p.add_argument("--agent", default="Master")
    p.add_argument("--task", default="", help="Descrição curta da tarefa")
    p.add_argument("--tokens", type=int, default=4000)
    p.add_argument("--output", type=int, default=800)
    p.add_argument("--tier", choices=list(PRICING.keys()), default=None)
    p.add_argument("--ledger", action="store_true", help="Mostra ledger")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.ledger:
        show_ledger()
        return

    if args.analyze:
        comp = classify_complexity(args.analyze)
        cost = estimate_cost(comp["tier"], args.tokens, args.output)
        if args.log:
            log_entry({
                "timestamp": datetime.now().isoformat(),
                "agent": args.agent,
                "task": args.analyze[:120],
                "kind": "analysis",
                **{k: comp[k] for k in ("tier", "complexity_score")},
                **{k: cost[k] for k in ("tokens_in", "tokens_out", "estimated_cost_usd", "model_suggested")},
            })
        if args.json:
            print(json.dumps({**comp, **cost}, indent=2, ensure_ascii=False))
        else:
            print(SEP)
            print("  🧭 MODEL ROUTER — análise de complexidade")
            print(SEP)
            print(f"  Missão: {args.analyze}")
            print(f"  Score complexidade : {comp['complexity_score']}")
            print(f"  Tier recomendado   : {comp['tier'].upper()}")
            print(f"  Modelo(s) sugerido : {', '.join(MODEL_HINT[comp['tier']])}")
            print(f"  Custo estimado     : ${cost['estimated_cost_usd']:.4f} "
                  f"({args.tokens} in / {args.output} out tokens)")
            print(f"  Racional           : {comp['rationale']}")
            print(SEP + "\n")
        return

    if args.log:
        tier = args.tier or classify_complexity(args.task)["tier"]
        cost = estimate_cost(tier, args.tokens, args.output)
        log_entry({
            "timestamp": datetime.now().isoformat(),
            "agent": args.agent,
            "task": (args.task or "geral")[:120],
            "kind": "usage",
            **cost,
        })
        print(f"[OK] ledger registrado @{args.agent} tier={tier} ≈ ${cost['estimated_cost_usd']:.4f}")
        return

    p.print_help()


if __name__ == "__main__":
    main()