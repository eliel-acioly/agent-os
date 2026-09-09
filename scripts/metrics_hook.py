#!/usr/bin/env python3
"""
metrics_hook.py — Observabilidade & Métricas dos Agentes (padrão OpenAI SDK Tracing / ADK observability)
Registra spans (evento, agente, duração, modelo, tokens estimados, decisão) no session_log.jsonl
e atualiza agent_metrics.json a cada handoff/entrega.

Uso:
  python .agents/scripts/metrics_hook.py --agent API --event span --duration-ms 850 --tokens 2400 --model claude-sonnet-4
  python .agents/scripts/metrics_hook.py --agent API --event task_completed --duration-ms 1234
  python .agents/scripts/metrics_hook.py --agent UI --event task_sent_to_logs --duration-ms 300
  python .agents/scripts/metrics_hook.py --status
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

AGENTS_DIR = Path(__file__).parent.parent
MEMORY_DIR = AGENTS_DIR / "memory"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"
METRICS_FILE = MEMORY_DIR / "agent_metrics.json"


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def current_model() -> str:
    return os.environ.get("AGENT_LLM_MODEL") or os.environ.get("LLM_MODEL") or "ide-llm"


def record_span(agent: str, event: str, duration_ms: float = 0, tokens: int = 0,
                decision: str = "", extra: dict = None) -> dict:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "event": event,
        "duration_ms": round(float(duration_ms), 2),
        "model": current_model(),
        "tokens_estimated": tokens,
    }
    if decision:
        entry["decision"] = decision
    if extra:
        entry.update(extra)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(SESSION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def bump_task(agent: str, kind: str = "task_completed") -> dict:
    metrics = load_json(METRICS_FILE)
    agents = metrics.setdefault("agents", {})
    ad = agents.setdefault(agent, {
        "tasks_completed": 0, "tasks_blocked": 0, "handoffs_issued": 0,
        "skill_score": 100, "last_active": None
    })
    field = "tasks_completed" if kind == "task_completed" else "tasks_blocked"
    ad[field] = ad.get(field, 0) + 1
    ad["last_active"] = datetime.now().isoformat()
    delta = 1 if kind == "task_completed" else -3
    ad["skill_score"] = max(50, min(100, ad.get("skill_score", 100) + delta))
    metrics["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(METRICS_FILE, metrics)
    event = "task_completed" if kind == "task_completed" else "task_blocked"
    record_span(agent, event=event, decision=event)
    return ad


def show_status():
    metrics = load_json(METRICS_FILE)
    agents = metrics.get("agents", {})
    print("\n=== AGENT METRICS STATUS (simples ===")
    total_done = total_blocked = 0
    for name in sorted(agents):
        a = agents[name]
        total_done += a.get("tasks_completed", 0)
        total_blocked += a.get("tasks_blocked", 0)
        print(f"  {name:>14}: score={a.get('skill_score', 100):>3} done={a.get('tasks_completed', 0):>3} "
              f"blocked={a.get('tasks_blocked', 0):>3} last={a.get('last_active', '—')}")
    print(f"  TOTAL: done={total_done} blocked={total_blocked}\n")


def main():
    p = argparse.ArgumentParser(description="metrics_hook — spans e métricas dos agentes.")
    p.add_argument("--agent", "-a", default="Master")
    p.add_argument("--event", "-e", default="span",
                   choices=["span", "session_opened", "memory_written", "rag_query", "handoff",
                            "task_completed", "task_blocked"])
    p.add_argument("--duration-ms", type=float, default=0)
    p.add_argument("--tokens", type=int, default=0)
    p.add_argument("--model", default=None)
    p.add_argument("--decision", default=None)
    p.add_argument("--status", action="store_true")
    args = p.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

    if args.event in ("task_completed", "task_blocked"):
        bump_task(args.agent, kind=args.event)
        print(f"[OK] métricas atualizadas para @{args.agent} ({args.event})")
        sys.exit(0)

    os.environ["AGENT_LLM_MODEL"] = args.model or os.environ.get("AGENT_LLM_MODEL", "")
    record_span(args.agent, args.event, duration_ms=args.duration_ms,
                tokens=args.tokens, decision=args.decision)
    print(f"[OK] span registrado: @{args.agent} {args.event} {args.duration_ms}ms tokens={args.tokens}")
    sys.exit(0)


if __name__ == "__main__":
    main()