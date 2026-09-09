#!/usr/bin/env python3
"""
task_graph.py — Task Graph do Agent-OS 2.0 (por tarefa, leve e auditável).

Toda tarefa complexa vira grafo: UNDERSTAND -> RETRIEVE -> IMPLEMENT ->
VERIFY -> DELIVER, com retries contados e dependências explícitas.
Permite paralelismo futuro (nós sem dependências conflitantes) e dá ao
thinking_loop o ciclo oficial DISCOVER..PROMOTE em artefatos.

Uso:
  python .agents/scripts/task_graph.py --new --mission "..." --agent API
  python .agents/scripts/task_graph.py --advance <task_id> --node RETRIEVE --status done
  python .agents/scripts/task_graph.py --show <task_id>
"""
import sys
import json
import argparse
import hashlib
import re
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from project_context import get_project_root, get_agents_dir, get_project_slug, get_project_memory_dir

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
TASKS_DIR = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR) / "tasks"

SEP = "=" * 70
NODES = ["UNDERSTAND", "RETRIEVE", "IMPLEMENT", "VERIFY", "DELIVER"]


def task_id_of(mission: str) -> str:
    h = hashlib.md5(mission.encode("utf-8")).hexdigest()[:8]
    words = re.sub(r"[^a-z0-9]+", "-", mission.lower()).strip("-")[:40] or "task"
    return f"{words}-{h}"


def _path(task_id: str) -> Path:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    return TASKS_DIR / f"{task_id}.json"


def new_task(mission: str, agent: str) -> dict:
    tid = task_id_of(mission)
    g = {
        "task_id": tid, "mission": mission, "agent": agent,
        "project": PROJECT_SLUG, "created_at": datetime.now().isoformat(),
        "nodes": {n: {"status": "pending", "retries": 0, "evidence": "",
                      "depends_on": [NODES[i - 1]] if i else []}
                  for i, n in enumerate(NODES)},
    }
    _path(tid).write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding="utf-8")
    return g


def load(task_id: str) -> dict:
    return json.loads(_path(task_id).read_text(encoding="utf-8"))


def advance(task_id: str, node: str, status: str, evidence: str = "") -> dict:
    g = load(task_id)
    if node not in g["nodes"]:
        raise ValueError(f"nó desconhecido: {node}")
    # Gate: dependências precisam estar done
    if status == "in_progress":
        for dep in g["nodes"][node]["depends_on"]:
            if g["nodes"][dep]["status"] != "done":
                raise ValueError(f"bloqueado: {dep} ainda {g['nodes'][dep]['status']}")
    g["nodes"][node]["status"] = status
    if evidence:
        g["nodes"][node]["evidence"] = evidence[:500]
    if status == "failed":
        g["nodes"][node]["retries"] += 1
    g["updated_at"] = datetime.now().isoformat()
    _path(task_id).write_text(json.dumps(g, indent=2, ensure_ascii=False), encoding="utf-8")
    return g


def ready_nodes(task_id: str) -> list:
    """Nós prontos para execução paralela (deps done, ainda não done)."""
    g = load(task_id)
    out = []
    for n in NODES:
        nd = g["nodes"][n]
        if nd["status"] == "done":
            continue
        if all(g["nodes"][d]["status"] == "done" for d in nd["depends_on"]):
            out.append(n)
    return out


def main():
    p = argparse.ArgumentParser(description="Task Graph por tarefa.")
    p.add_argument("--new", action="store_true")
    p.add_argument("--mission", "-m", default="")
    p.add_argument("--agent", "-a", default="Master")
    p.add_argument("--advance", default="", help="task_id para avançar nó")
    p.add_argument("--node", default="")
    p.add_argument("--status", default="done", choices=["pending", "in_progress", "done", "failed", "blocked"])
    p.add_argument("--evidence", default="")
    p.add_argument("--show", default="")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.new:
        if not args.mission:
            p.print_help()
            sys.exit(1)
        g = new_task(args.mission, args.agent.replace("@", ""))
        print(json.dumps(g, indent=2, ensure_ascii=False) if args.json else
              f"{SEP}\n  TASK GRAPH [{g['task_id']}]\n{SEP}\n" +
              "\n".join(f"  [ ] {n}" for n in NODES) + f"\n{SEP}")
        return
    if args.advance:
        try:
            g = advance(args.advance, args.node, args.status, args.evidence)
        except ValueError as e:
            print(f"[BLOQUEADO] {e}")
            sys.exit(2)
        print(json.dumps(g["nodes"], indent=2, ensure_ascii=False) if args.json else
              f"[OK] {args.node} -> {args.status} | prontos: {ready_nodes(args.advance)}")
        return
    if args.show:
        g = load(args.show)
        if args.json:
            print(json.dumps(g, indent=2, ensure_ascii=False))
        else:
            print(f"{SEP}\n  TASK {g['task_id']} ({g['project']})\n{SEP}")
            for n in NODES:
                nd = g["nodes"][n]
                print(f"  [{nd['status']}] {n} (retries={nd['retries']}) {nd['evidence'][:80]}")
            print(SEP)
        return
    p.print_help()


if __name__ == "__main__":
    main()
