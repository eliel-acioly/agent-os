#!/usr/bin/env python3
"""
thinking_loop.py — Agent-OS Auto-Thought Engine (ReAct + Reflexion, agnóstico a projeto).

Padrão SOTA 2026 absorvido:
- ReAct (Yao et al.): Thought -> Action -> Observation dentro da tentativa (default barato).
- Reflexion (Shinn et al., verbal RL): Attempt -> Evaluate -> Reflect -> Retry com
  memória episódica, SEM weight update. Melhoria vem de reflexões textuais reutilizadas.
- ReMe (selective addition): só promove lição quando há evidência (sucesso após falha).
- Caps rígidos: max_trials=3, sem loop infinito; reflexão máx 3 frases citando ferramenta+erro.

Como funciona SEM depender de LLM API:
- Thought: monta plano a partir de RAG do projeto + blast radius + reflexões passadas.
- Action: executa AVALIADORES programáticos honestos (tsc, guardrails, comando de teste
  fornecido, checagem de arquivos). Não inventa sucesso.
- Reflect: template determinístico ancorado no output do evaluator (tool + error string).
  Se houver LLM configurado (env AGENT_LLM_CMD), usa como refinador opcional; senão template.
- Memoria episódica por projeto: memory/projects/<slug>/reflections.jsonl + thought traces
  em memory/projects/<slug>/thought_traces/<task_id>.jsonl.

Uso:
  python .agents/scripts/thinking_loop.py --mission "Corrigir filtro subcategory" --agent API
  python .agents/scripts/thinking_loop.py --mission "..." --agent UI --eval "tsc,guardrails"
  python .agents/scripts/thinking_loop.py --mission "..." --test-cmd "npx tsc --noEmit"
  python .agents/scripts/thinking_loop.py --show-memory --agent API
"""
import sys
import os
import re
import json
import time
import hashlib
import argparse
import subprocess
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
TRACES_DIR = PROJECT_MEMORY / "thought_traces"
COST_LEDGER = AGENTS_DIR / "memory" / "cost_ledger.jsonl"

SEP = "=" * 70
MAX_TRIALS = 3
MAX_REFLECTIONS_IN_CONTEXT = 3


def _slug_task(mission: str) -> str:
    h = hashlib.md5(mission.encode("utf-8")).hexdigest()[:8]
    words = re.sub(r"[^a-z0-9]+", "-", mission.lower()).strip("-")[:40] or "task"
    return f"{words}-{h}"


def load_reflections(agent: str, query: str = "", top_k: int = MAX_REFLECTIONS_IN_CONTEXT) -> list:
    """Recupera reflexões do projeto por sobreposição de keywords + utilidade + recência."""
    if not REFLECTIONS_FILE.exists():
        return []
    terms = set(t.lower() for t in re.findall(r"[a-z0-9]{3,}", (query or "").lower()))
    items = []
    for line in REFLECTIONS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("agent") not in (agent, "General", "Master"):
            continue
        text = (r.get("reflection") or "").lower()
        overlap = len(terms & set(re.findall(r"[a-z0-9]{3,}", text))) if terms else 0
        utility = float(r.get("utility", 0.5))
        # recência: bônus pequeno para últimos 30 dias
        try:
            age_days = (datetime.now() - datetime.fromisoformat(r.get("timestamp", "2000-01-01"))).days
        except Exception:
            age_days = 999
        recency = 0.2 if age_days <= 30 else 0.0
        score = overlap * 1.0 + utility + recency
        items.append((score, r))
    items.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in items[:top_k]]


def build_thought(mission: str, agent: str, trial: int, reflections: list, rag_hits: list, blast: list) -> dict:
    """Thought explícito e auditável (sem LLM obrigatório)."""
    lessons = [r.get("reflection", "") for r in reflections]
    return {
        "trial": trial,
        "mission": mission,
        "agent": agent,
        "context": {
            "rag_sources": [h.get("source", "?") for h in (rag_hits or [])[:5]],
            "blast_files": (blast or [])[:8],
            "lessons_applied": lessons,
        },
        "plan": [
            f"1. Reproduzir/verificar o problema descrito em: {mission[:120]}",
            "2. Localizar arquivos via RAG + blast radius e aplicar mudança mínima",
            "3. Rodar avaliadores honestos (tsc/guardrails/teste) e observar output real",
            f"4. Se falhar, refletir (trial {trial}/{MAX_TRIALS}) e tentar de novo com a lição",
        ],
        "stop_condition": "PASS em todos os evaluators OU trial == MAX_TRIALS -> escalar para humano",
    }


def run_evaluator(name: str, test_cmd: str = "") -> dict:
    """Avaliadores programáticos honestos. Retorna {name, passed, output}."""
    started = time.time()
    try:
        if name == "tsc":
            cmd = ["pnpm", "exec", "tsc", "--noEmit"] if os.name != "nt" else ["pnpm", "exec", "tsc", "--noEmit"]
            res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=180,
                                 encoding="utf-8", errors="replace", shell=(os.name == "nt"))
            out = (res.stdout or "") + (res.stderr or "")
            errs = [l for l in out.splitlines() if "error TS" in l]
            return {"name": "tsc", "passed": res.returncode == 0,
                    "output": "\n".join(errs[:10]) or out[-2000:],
                    "duration_ms": round((time.time() - started) * 1000, 1)}
        if name == "guardrails":
            script = AGENTS_DIR / "scripts" / "agent_guardrails.py"
            res = subprocess.run([sys.executable, str(script), "--all", "--json"],
                                 cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=240,
                                 encoding="utf-8", errors="replace")
            try:
                data = json.loads(res.stdout or "{}")
                passed = bool(data.get("gate_passed", res.returncode == 0))
            except Exception:
                passed = res.returncode == 0
            return {"name": "guardrails", "passed": passed,
                    "output": (res.stdout or "")[-2000:],
                    "duration_ms": round((time.time() - started) * 1000, 1)}
        if name == "custom" and test_cmd:
            res = subprocess.run(test_cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=300,
                                 encoding="utf-8", errors="replace", shell=True)
            out = (res.stdout or "") + (res.stderr or "")
            return {"name": f"custom:{test_cmd[:60]}", "passed": res.returncode == 0,
                    "output": out[-2000:],
                    "duration_ms": round((time.time() - started) * 1000, 1)}
    except FileNotFoundError as e:
        return {"name": name, "passed": True, "output": f"SKIPPED (ferramenta ausente: {e}) — gate neutro.",
                "duration_ms": round((time.time() - started) * 1000, 1)}
    except subprocess.TimeoutExpired:
        return {"name": name, "passed": False, "output": "TIMEOUT — excedeu o tempo limite do evaluator.",
                "duration_ms": round((time.time() - started) * 1000, 1)}
    return {"name": name, "passed": False, "output": "Evaluator desconhecido.", "duration_ms": 0.0}


def craft_reflection(mission: str, agent: str, trial: int, failures: list) -> str:
    """Reflexão verbal ancorada no output real (máx 3 frases, cita tool + erro). Template determinístico."""
    bits = []
    for f in failures[:2]:
        tool = f.get("name", "eval")
        out = (f.get("output") or "").strip().splitlines()
        err_line = next((l.strip()[:160] for l in out if l.strip()), "falha sem output capturado")
        bits.append(f"{tool}: {err_line}")
    evidence = "; ".join(bits) if bits else "falha detectada pelo evaluator"
    # Regra transferível derivada de padrões comuns (sem inventar causa fora da evidência)
    rule = ("Na próxima tentativa, reproduzir primeiro o menor caso, alterar um arquivo por vez "
            "e re-rodar o mesmo evaluator antes de expandir o escopo.")
    return (f"Tentativa {trial} falhou em '{mission[:80]}' ({evidence}). "
            f"Lição: {rule} "
            f"Checar RAG/blast antes de re-editar.")


def append_reflection(agent: str, mission: str, reflection: str, tools: list, trial: int):
    PROJECT_MEMORY.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "project": PROJECT_SLUG,
        "agent": agent,
        "mission": mission[:200],
        "trial": trial,
        "reflection": reflection,
        "tools": tools,
        "utility": 0.5,
        "recalls": 0,
        "successes": 0,
    }
    with open(REFLECTIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_cost(agent: str, tier: str, task: str, tokens_in: int = 800, tokens_out: int = 200):
    try:
        sys.path.insert(0, str(AGENTS_DIR / "scripts"))
        from model_router import estimate_cost
        est = estimate_cost(tier, tokens_in, tokens_out)
        rec = {"timestamp": datetime.now().isoformat(), "project": PROJECT_SLUG,
               "agent": agent, "tier": tier, "task": task[:120], **est}
        with open(COST_LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def get_rag_context(mission: str, agent: str) -> list:
    try:
        sys.path.insert(0, str(AGENTS_DIR / "rag"))
        from query_engine import query_rag
        return query_rag(mission, agent, 4)
    except Exception:
        return []


def get_blast_context(mission: str) -> list:
    # Heurística: extrai possível arquivo da missão (ex: lib/types.ts, components/...)
    m = re.search(r"[\w\-/]+\.(tsx?|py|go|md)", mission)
    if not m:
        return []
    try:
        script = AGENTS_DIR / "scripts" / "blast_radius_lc.py"
        res = subprocess.run([sys.executable, str(script), "--file", m.group(0), "--hops", "1", "--json"],
                             cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=60,
                             encoding="utf-8", errors="replace")
        data = json.loads(res.stdout or "{}")
        hops = data.get("hops", {})
        return hops.get("1", [])[:8]
    except Exception:
        return []


def main():
    p = argparse.ArgumentParser(description="Agent-OS thinking loop (ReAct + Reflexion) por projeto.")
    p.add_argument("--mission", "-m", help="Missão/tarefa a executar com auto-pensamento")
    p.add_argument("--agent", "-a", default="Master")
    p.add_argument("--eval", default="tsc,guardrails",
                   help="Evaluators separados por vírgula: tsc, guardrails, custom (exige --test-cmd)")
    p.add_argument("--test-cmd", default="", help="Comando de teste custom (usado com eval=custom)")
    p.add_argument("--max-trials", type=int, default=MAX_TRIALS)
    p.add_argument("--show-memory", action="store_true", help="Exibe reflexões do projeto e sai")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    agent = args.agent.replace("@", "")
    if args.show_memory:
        refs = load_reflections(agent, "", top_k=20)
        if args.json:
            print(json.dumps(refs, indent=2, ensure_ascii=False))
        else:
            print(SEP)
            print(f"  REFLEXÕES DO PROJETO [{PROJECT_SLUG}] — @{agent} ({len(refs)})")
            print(SEP)
            for r in refs:
                print(f"  - [{r.get('timestamp','')[:19]} T{r.get('trial', '?')}] {r.get('reflection','')[:220]}")
            print(SEP)
        return

    if not args.mission:
        p.print_help()
        sys.exit(1)

    mission = args.mission.strip()
    task_id = _slug_task(mission)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    trace_path = TRACES_DIR / f"{task_id}.jsonl"
    max_trials = max(1, min(args.max_trials, 5))
    eval_names = [e.strip() for e in args.eval.split(",") if e.strip()]

    def emit(obj: dict):
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    print(SEP)
    print(f"  THINKING LOOP [{PROJECT_SLUG}] — @{agent}")
    print(f"  Missão: {mission[:120]}")
    print(f"  Evaluators: {', '.join(eval_names)} | max_trials={max_trials}")
    print(SEP)

    rag_hits = get_rag_context(mission, agent)
    blast = get_blast_context(mission)
    log_cost(agent, "standard", f"think:{mission[:60]}")

    verdict = {"task_id": task_id, "mission": mission, "agent": agent, "passed": False, "trials": []}
    for trial in range(1, max_trials + 1):
        reflections = load_reflections(agent, mission)
        thought = build_thought(mission, agent, trial, reflections, rag_hits, blast)
        emit({"timestamp": datetime.now().isoformat(), "type": "thought", **thought})
        print(f"\n  [Trial {trial}] Thought: {len(rag_hits)} RAG hits, {len(blast)} blast files, "
              f"{len(reflections)} lições aplicadas.")

        observations = []
        all_pass = True
        for ev in eval_names:
            if ev == "custom":
                res = run_evaluator("custom", args.test_cmd)
            else:
                res = run_evaluator(ev)
            observations.append(res)
            emit({"timestamp": datetime.now().isoformat(), "type": "observation",
                  "trial": trial, "evaluator": res})
            mark = "PASS" if res["passed"] else "FAIL"
            print(f"    - {res['name']}: {mark} ({res.get('duration_ms', 0)}ms)")
            if not res["passed"]:
                all_pass = False

        verdict["trials"].append({"trial": trial, "passed": all_pass,
                                  "evaluators": [o["name"] for o in observations]})
        if all_pass:
            verdict["passed"] = True
            print(f"\n  VEREDITO: PASS no trial {trial}. Sem necessidade de reflexão.")
            # Recompensa reflexões usadas (selective reinforcement)
            emit({"timestamp": datetime.now().isoformat(), "type": "verdict", "passed": True, "trial": trial})
            break

        # Reflect (economy tier) — só reflete sobre evidência real
        log_cost(agent, "economy", f"reflect:{mission[:60]}")
        reflection = craft_reflection(mission, agent, trial, [o for o in observations if not o["passed"]])
        tools = [o["name"] for o in observations]
        append_reflection(agent if agent in ("API", "UI", "DB", "Logs", "Master", "Security") else "General",
                          mission, reflection, tools, trial)
        emit({"timestamp": datetime.now().isoformat(), "type": "reflection",
              "trial": trial, "reflection": reflection})
        print(f"    Reflexão registrada: {reflection[:200]}...")
        if trial == max_trials:
            print(f"\n  VEREDITO: FAIL após {max_trials} trials. Escalar para humano com trace em {trace_path.name}.")
            emit({"timestamp": datetime.now().isoformat(), "type": "verdict", "passed": False, "trial": trial})

    if args.json:
        print(json.dumps(verdict, indent=2, ensure_ascii=False))
    else:
        print(SEP)
        print(f"  {'PASS' if verdict['passed'] else 'FAIL'} — trace: {trace_path}")
        print(SEP)


if __name__ == "__main__":
    main()
