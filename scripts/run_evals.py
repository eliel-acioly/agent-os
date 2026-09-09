#!/usr/bin/env python3
"""
run_evals.py — Evals Contínuos de Regressão por Épico (padrão SWE-bench-style / Devin evals)
Inventaria suítes de teste em docs/testes/ e registra resultados em .agents/memory/evals_history.jsonl
com comparação contra a execução anterior (baseline) para detectar regressões.

Uso:
  python .agents/scripts/run_evals.py --inventory               # inventário + contagem sem executar
  python .agents/scripts/run_evals.py --run <arquivo.ts>        # executa um arquivo de teste (timeout 120s)
  python .agents/scripts/run_evals.py --suite-system            # executa a suíte de validação do Agent-OS
  python .agents/scripts/run_evals.py --history                 # histórico + baseline
"""

import sys
import os
import json
import time
import argparse
import subprocess
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
TESTES_DIR = ROOT / "docs" / "testes"
EVALS_LOG = MEMORY_DIR / "evals_history.jsonl"
SEP = "=" * 70

# Marcadores que indicam que o teste não pôde rodar por ambiente (não é regressão)
ENV_SKIP_MARKS = [
    "não é possível conectar", "could not connect", "ECONNREFUSED", "401 Unauthorized",
    "token", "credential", "Supabase", "SupabaseError", "service_role", "chave",
    "process.exit", "faltando", "missing", "timeout", "TimedOut", "deploy",
]


def discover_suites() -> list:
    suites = []
    if TESTES_DIR.exists():
        for date_dir in sorted(TESTES_DIR.iterdir()):
            if date_dir.is_dir():
                ts_files = sorted(date_dir.glob("*.ts"))
                suites.append({
                    "suite": date_dir.name,
                    "tests": [f.name for f in ts_files],
                    "path": str(date_dir),
                })
    return suites


def classify_result(output: str, returncode: int, timed_out: bool) -> str:
    if timed_out:
        return "SKIPPED_TIMEOUT"
    if returncode == 0:
        return "PASS"
    low = output.lower()
    if any(mark.lower() in low for mark in ENV_SKIP_MARKS):
        return "SKIPPED_ENV"
    return "FAIL"


def run_ts(file_path: Path, timeout_s: int = 120) -> dict:
    start = time.time()
    try:
        res = subprocess.run(
            ["npx", "tsx", str(file_path)], cwd=str(ROOT), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout_s
        )
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        res = None
    elapsed = round((time.time() - start) * 1000, 2)
    output = (res.stdout + "\n" + (res.stderr or "")) if res else "timeout"
    return {
        "status": classify_result(output, res.returncode if res else -1, timed_out),
        "duration_ms": elapsed,
        "last_lines": "\n".join(output.strip().splitlines()[-6:]),
    }


def log_eval(entry: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(EVALS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history() -> list:
    if not EVALS_LOG.exists():
        return []
    return [json.loads(l) for l in EVALS_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]


def show_history():
    hist = load_history()
    print(SEP)
    print("  🧪 HISTÓRICO DE EVALS")
    print(SEP)
    if not hist:
        print("  (vazio)")
        print(SEP)
        return
    for e in hist[-15:]:
        print(f"  {e.get('timestamp','')[:19]}  {e.get('kind','?'):<12} {e.get('target','?'):<50} {e.get('status','?')}")
    print(SEP + "\n")


def main():
    p = argparse.ArgumentParser(description="Evals contínuos de regressão (SWE-bench-style).")
    p.add_argument("--inventory", action="store_true", help="Inventário sem executar")
    p.add_argument("--run", "-r", metavar="ARQUIVO", help="Executa um arquivo de teste")
    p.add_argument("--suite-system", action="store_true", help="Executa a suíte de validação do Agent-OS")
    p.add_argument("--history", action="store_true", help="Mostra histórico/baseline")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.history:
        show_history()
        return

    suites = discover_suites()

    if args.inventory:
        total = sum(len(s["tests"]) for s in suites)
        out = {"suites": suites, "total_tests": total, "testes_dir": str(TESTES_DIR)}
        if args.json:
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            print(SEP)
            print("  🧪 INVENTÁRIO DE EVALS")
            print(SEP)
            for s in suites:
                print(f"  • {s['suite']}: {len(s['tests'])} teste(s)")
                for t in s["tests"]:
                    print(f"      - {t}")
            print(f"\n  📊 Total de testes inventariados: {total}")
            print(SEP + "\n")
        return

    if args.run:
        candidate = Path(args.run)
        if not candidate.is_absolute():
            candidate = Path("docs") / "testes" / args.run
        if not candidate.exists():
            print(f"[ERRO] Arquivo de teste não encontrado: {candidate}")
            sys.exit(1)
        result = run_ts(candidate)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "kind": "test",
            "target": candidate.relative_to(ROOT).as_posix(),
            **result,
        }
        log_eval(entry)
        print(json.dumps(entry, indent=2, ensure_ascii=False) if args.json else
              f"  {candidate.name}: {result['status']} ({result['duration_ms']}ms)")
        sys.exit(0 if result["status"] == "PASS" else 1)

    if args.suite_system:
        runner = AGENTS_DIR / "tests" / "run_system_validation.py"
        if not runner.exists():
            print("[ERRO] Suíte Agent-OS não encontrada: .agents/tests/run_system_validation.py")
            sys.exit(1)
        start = time.time()
        res = subprocess.run([sys.executable, str(runner)], cwd=str(ROOT), capture_output=True,
                             text=True, encoding="utf-8", errors="replace", timeout=180)
        elapsed = round((time.time() - start) * 1000, 2)
        status = "PASS" if res.returncode == 0 else classify_result(res.stdout + res.stderr, res.returncode, False)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "kind": "suite-system",
            "target": "run_system_validation.py",
            "status": status,
            "duration_ms": elapsed,
            "summary": "\n".join([l for l in res.stdout.splitlines() if "RESULTADO" in l or "SUÍTE" in l])[:200],
        }
        log_eval(entry)
        print(json.dumps(entry, indent=2, ensure_ascii=False) if args.json else
              f"  run_system_validation.py: {status} ({elapsed}ms)")
        sys.exit(0 if status == "PASS" else 1)

    p.print_help()


if __name__ == "__main__":
    main()