#!/usr/bin/env python3
"""
evolve_gated.py — Agent-OS Eval-Gated Evolution (por projeto).

Diferente do auto_evolve.py (audita e relata), este PROMOVE mudanças somente com
evidência: cada proposta é um patch de escopo seguro (skills/, rules/, docs/) que
só é aplicado se guardrails + checks passarem; senão rollback automático.

Segurança:
- Allowlist de paths: skills/**, rules/**, docs/architecture/**. NUNCA toca app/,
  components/, lib/, src/, supabase/, scripts/ de produção sem --allow-unsafe + review.
- Toda promoção gera backup em memory/projects/<slug>/_evolve_backups/ + ledger em
  self_improvement/evolution_history.json com verdict e evidência.
- Gate: agent_guardrails --all + py_compile dos arquivos tocados + (opcional) teste.

Uso:
  python .agents/scripts/evolve_gated.py --propose --file skills/antecipia-ui/SKILL.md --note "..."
  # edite o arquivo proposto, depois:
  python .agents/scripts/evolve_gated.py --promote --file skills/antecipia-ui/SKILL.md
  python .agents/scripts/evolve_gated.py --history
"""
import sys
import json
import shutil
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
BACKUP_DIR = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR) / "_evolve_backups"
EVOLUTION_LOG = AGENTS_DIR / "self_improvement" / "evolution_history.json"
STAGING_FILE = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR) / "_evolve_staging.json"

SEP = "=" * 70
SAFE_PREFIXES = ("skills/", "rules/", "docs/architecture/", "docs/agent-cards/")


def _target_in_agents(rel: str) -> Path:
    # rel como "skills/antecipia-ui/SKILL.md" (dentro do agent-os)
    return AGENTS_DIR / rel


def _is_safe(rel: str, allow_unsafe: bool = False) -> bool:
    if rel.startswith(tuple(SAFE_PREFIXES)):
        return True
    return bool(allow_unsafe)


def _load_staging() -> dict:
    if STAGING_FILE.exists():
        try:
            return json.loads(STAGING_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_staging(data: dict):
    STAGING_FILE.parent.mkdir(parents=True, exist_ok=True)
    STAGING_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _log_cycle(entry: dict):
    try:
        hist = json.loads(EVOLUTION_LOG.read_text(encoding="utf-8")) if EVOLUTION_LOG.exists() else []
    except Exception:
        hist = []
    hist.append(entry)
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    EVOLUTION_LOG.write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")


def run_gate(extra_test: str = "") -> dict:
    """Gate honesto: py_compile implícito pelos checks + guardrails + teste opcional."""
    results = {}
    # 1. guardrails
    try:
        script = AGENTS_DIR / "scripts" / "agent_guardrails.py"
        res = subprocess.run([sys.executable, str(script), "--all", "--json"],
                             cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=240,
                             encoding="utf-8", errors="replace")
        data = json.loads(res.stdout or "{}")
        results["guardrails"] = bool(data.get("gate_passed", res.returncode == 0))
        results["guardrails_detail"] = [{g.get("name"): g.get("passed")} for g in data.get("guards", [])]
    except Exception as e:
        results["guardrails"] = False
        results["guardrails_detail"] = [f"erro: {e}"]
    # 2. teste extra opcional
    if extra_test:
        try:
            res = subprocess.run(extra_test, cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                                 timeout=300, encoding="utf-8", errors="replace", shell=True)
            results["extra_test"] = res.returncode == 0
            results["extra_output"] = ((res.stdout or "") + (res.stderr or ""))[-1500:]
        except Exception as e:
            results["extra_test"] = False
            results["extra_output"] = str(e)
    results["passed"] = all(v is True for k, v in results.items() if k in ("guardrails", "extra_test"))
    return results


def main():
    p = argparse.ArgumentParser(description="Evolução com gate de avaliação (escopo seguro).")
    p.add_argument("--propose", action="store_true", help="Registra proposta e faz backup do original")
    p.add_argument("--promote", action="store_true", help="Roda gate e promove (ou rollback)")
    p.add_argument("--file", "-f", default="", help="Path relativo no agent-os (skills/..., rules/...)")
    p.add_argument("--note", default="", help="Motivo da mudança")
    p.add_argument("--test-cmd", default="", help="Teste extra para o gate")
    p.add_argument("--allow-unsafe", action="store_true", help="Permite fora da allowlist (exige review humano)")
    p.add_argument("--history", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.history:
        try:
            hist = json.loads(EVOLUTION_LOG.read_text(encoding="utf-8")) if EVOLUTION_LOG.exists() else []
        except Exception:
            hist = []
        mine = [h for h in hist if h.get("project") == PROJECT_SLUG][-10:]
        print(json.dumps(mine, indent=2, ensure_ascii=False) if args.json else
              f"{SEP}\n  EVOLUTION HISTORY [{PROJECT_SLUG}] ({len(mine)} recentes)\n{SEP}\n" +
              "\n".join(f"  - {h.get('timestamp','')[:19]} {h.get('verdict','?')} {h.get('file','')}" for h in mine) + f"\n{SEP}")
        return

    if not args.file:
        p.print_help()
        sys.exit(1)
    rel = args.file.replace("\\", "/").lstrip("./")
    if rel.startswith(".agents/"):
        rel = rel[len(".agents/"):]
    if not _is_safe(rel, args.allow_unsafe):
        print(f"[BLOQUEADO] '{rel}' fora da allowlist {SAFE_PREFIXES}. Use --allow-unsafe com review humano.")
        sys.exit(2)
    target = _target_in_agents(rel)
    if not target.exists():
        print(f"[ERRO] Arquivo não existe: {target}")
        sys.exit(1)

    if args.propose:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = BACKUP_DIR / f"{rel.replace('/', '__')}__{stamp}.bak"
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        st = _load_staging()
        st[rel] = {"backup": str(backup), "note": args.note, "proposed_at": datetime.now().isoformat()}
        _save_staging(st)
        print(f"[OK] Proposta registrada: {rel}\n     Backup: {backup.name}\n     Edite o arquivo e rode --promote.")
        return

    if args.promote:
        st = _load_staging()
        if rel not in st:
            print(f"[ERRO] Sem proposta registrada para '{rel}'. Rode --propose primeiro.")
            sys.exit(1)
        # py_compile se for .py
        if target.suffix == ".py":
            res = subprocess.run([sys.executable, "-m", "py_compile", str(target)], capture_output=True, text=True)
            if res.returncode != 0:
                print(f"[GATE FAIL] py_compile: {res.stderr[:500]}")
                shutil.copy2(st[rel]["backup"], target)
                print("[ROLLBACK] Original restaurado.")
                _log_cycle({"timestamp": datetime.now().isoformat(), "project": PROJECT_SLUG,
                            "file": rel, "verdict": "REJECTED", "reason": "py_compile"})
                sys.exit(3)
        gate = run_gate(args.test_cmd)
        if gate["passed"]:
            st.pop(rel, None)
            _save_staging(st)
            _log_cycle({"timestamp": datetime.now().isoformat(), "project": PROJECT_SLUG,
                        "file": rel, "note": st.get(rel, {}).get("note", args.note),
                        "verdict": "PROMOTED", "gate": gate})
            print(f"[PROMOTED] {rel} — gate PASS (guardrails + testes).")
        else:
            shutil.copy2(st[rel]["backup"], target)
            st.pop(rel, None)
            _save_staging(st)
            _log_cycle({"timestamp": datetime.now().isoformat(), "project": PROJECT_SLUG,
                        "file": rel, "verdict": "REJECTED_ROLLBACK", "gate": gate})
            print(f"[REJECTED] Gate FAIL — rollback executado para {rel}.")
            print(json.dumps(gate, indent=2, ensure_ascii=False)[:2000])
            sys.exit(4)
        return

    p.print_help()


if __name__ == "__main__":
    main()
