#!/usr/bin/env python3
"""
agent_guardrails.py — Software Factory Gate (padrão OpenAI Agents SDK Guardrails / Claude Code verification-first)
Guarda o loop dos agentes com validação automática de ENTRADA e SAÍDA (fail-fast):
  1. --handoff  : integridade do HANDOFF.md (máquina de estados da esteira).
  2. --secrets  : varredura de secrets vazados em código de produção (app/, lib/, scripts/).
  3. --spec     : auditoria de SPECs formais via spec_linter.py (critério de entrada).
  4. --rag      : saúde do índice RAG (ChromaDB ou fallback SQLite híbrido).
  5. --tsc      : checagem de tipagem TypeScript (pnpm exec tsc --noEmit) quando disponível.
  6. --all      : executa todas as guardas e retorna gate PASS/FAIL composto.

Uso:
  python .agents/scripts/agent_guardrails.py --handoff
  python .agents/scripts/agent_guardrails.py --secrets
  python .agents/scripts/agent_guardrails.py --all --json
"""

import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
try:
    from project_context import get_project_root, get_agents_dir, get_project_slug, get_index_dir
    PROJECT_ROOT = get_project_root()
    AGENTS_DIR = get_agents_dir()
    PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
except Exception:
    AGENTS_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = AGENTS_DIR.parent
    PROJECT_SLUG = "proj"

ROOT = PROJECT_ROOT
SEPARATOR = "=" * 70


# ---------------------------------------------------------------------------
# 1. Guarda de ENTRADA — Integridade do HANDOFF.md (FSM da esteira)
# ---------------------------------------------------------------------------
def check_handoff() -> dict:
    handoff_path = ROOT / "HANDOFF.md"
    report = {"name": "handoff", "passed": True, "findings": []}

    if not handoff_path.exists():
        report["passed"] = False
        report["findings"].append("HANDOFF.md não encontrado na raiz do workspace.")
        return report

    content = handoff_path.read_text(encoding="utf-8", errors="ignore")
    steps = re.findall(r"## \d+\.\s*Passo \d+ \(@([A-Za-z0-9_]+)\)", content)

    if len(steps) >= 2:
        report["findings"].append(f"Esteira com {len(steps)} passos: {' → '.join(steps)}")
    elif content and ("Status do Workspace" in content or "Agente Responsável" in content):
        # Formato operacional (auditoria/handoff concluído) — gateway neutro, sem falha dura.
        report["passes_note"] = "HANDOFF em formato operacional/auditado (pronto para leitura por @Master/@CTO)."
        report["findings"].append("HANDOFF presente; formatação 'Passo N (@Agente)' será exigida no próximo épico.")
    else:
        report["passed"] = False
        report["findings"].append("HANDOFF sem estrutura canônica (neither Passo N nor formato operacional).")

    statuses = re.findall(r"\*\*Status:\*\*\s*([^\n]+)", content)
    pendentes = [s for s in statuses if "CONCLU" not in s.upper() and "PASS" not in s.upper()]
    if pendentes:
        report["passes_note"] = f"{len(pendentes)} passo(s) aguardando conclusão no HANDOFF.md."

    return report


# ---------------------------------------------------------------------------
# 2. Guarda de SAÍDA — Varredura de Secrets em código de produção
# ---------------------------------------------------------------------------
SECRET_PATTERNS = [
    ("SUPABASE_SERVICE_ROLE_KEY_INLINE", re.compile(r"(?:SUPABASE_SERVICE_ROLE_KEY|SERVICE_ROLE)\s*[=:]\s*[\"'][^\"']{10,}[\"']", re.I)),
    ("OPENAI_SK", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("AWS_AKIA", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("GENERIC_PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
]


def check_secrets() -> dict:
    report = {"name": "secrets", "passed": True, "findings": []}
    target_dirs = ["app", "lib", "scripts"]
    skip_dirs = {"node_modules", ".next", "dist", "build", "__pycache__", ".git", "venv", ".venv"}
    scanned = 0

    for target in target_dirs:
        base = ROOT / target
        if not base.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for fname in filenames:
                if not fname.lower().endswith((".ts", ".tsx", ".js", ".jsx", ".py")):
                    continue
                if ".env" in fname.lower():
                    continue
                full = Path(dirpath) / fname
                scanned += 1
                try:
                    text = full.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for name, pattern in SECRET_PATTERNS:
                    for m in pattern.finditer(text):
                        snippet_line = text.count("\n", 0, m.start()) + 1
                        matched_value = m.group(0)
                        # Falso positivo: interpolações de ambiente (${VAR}, process.env.X, config.X) NÃO são secrets.
                        if re.search(r"\$\{[^}]+\}|\bprocess\.env\b|\bconfig\.[A-Za-z_]+|\.env\.", matched_value):
                            continue
                        snippet = matched_value[:120].replace("|", "/")
                        report["findings"].append(
                            f"{full.relative_to(ROOT)}:{snippet_line} [{name}] {snippet}"
                        )

    if report["findings"]:
        report["passed"] = False
    else:
        report["findings"].append(f"{scanned} arquivos de código varridos — nenhum secret exposto.")
    return report


# ---------------------------------------------------------------------------
# 3. Guarda de ENTRADA — SPECs Formais (Spec-Driven Development)
# ---------------------------------------------------------------------------
def check_specs() -> dict:
    report = {"name": "specs", "passed": True, "findings": []}
    specs_dir = ROOT / "docs" / "specs"

    if not specs_dir.exists():
        report["passed"] = True
        report["findings"].append("Sem diretório docs/specs (specs são adotadas por épico). Gate neutro.")
        return report

    spec_files = sorted(specs_dir.glob("SPEC-*.md"))
    if not spec_files:
        report["findings"].append("Nenhuma SPEC-*.md encontrada.")
        return report

    linter = AGENTS_DIR / "scripts" / "spec_linter.py"
    approved = 0
    for spec in spec_files:
        try:
            res = subprocess.run(
                [sys.executable, str(linter), "--file", str(spec), "--json"],
                capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace",
            )
            data = json.loads(res.stdout) if res.stdout.strip() else {}
            ok = bool(data.get("approved"))
            approved += 1 if ok else 0
            marker = "🟢" if ok else "🔴"
            report["findings"].append(f"{marker} {spec.name} — {data.get('score', '?')}%")
        except Exception as e:
            report["findings"].append(f"⚠️  Erro ao validar {spec.name}: {e}")

    report["passed"] = approved == len(spec_files)
    report["passes_note"] = f"{approved}/{len(spec_files)} SPECs aprovadas."
    return report


# ---------------------------------------------------------------------------
# 4. Guarda de SAÍDA — Saúde do Índice RAG (busca vetorial / fallback)
# ---------------------------------------------------------------------------
def check_rag() -> dict:
    report = {"name": "rag", "passed": True, "findings": []}
    try:
        index_dir = get_index_dir(PROJECT_ROOT, AGENTS_DIR)
    except Exception:
        index_dir = AGENTS_DIR / "rag" / "knowledge" / "project_index"
    legacy_dir = AGENTS_DIR / "rag" / "knowledge" / "project_index"
    sqlite = index_dir / "chroma.sqlite3"
    legacy_sqlite = legacy_dir / "chroma.sqlite3"

    active = None
    if sqlite.exists() and sqlite.stat().st_size > 0:
        active = sqlite
        report["findings"].append(
            f"Índice SQLite do RAG OK por projeto [{PROJECT_SLUG}] ({round(sqlite.stat().st_size / 1024, 1)} KB) — fallback híbrido disponível."
        )
    elif legacy_sqlite.exists() and legacy_sqlite.stat().st_size > 0:
        active = legacy_sqlite
        report["findings"].append(
            f"Índice legado OK ({round(legacy_sqlite.stat().st_size / 1024, 1)} KB) — migre com: python .agents/rag/indexer.py --target all"
        )
    else:
        report["passed"] = False
        report["findings"].append("Índice do RAG ausente. Execute: python .agents/rag/indexer.py --target all")

    try:
        import chromadb
        shown = False
        for base in ([index_dir] if index_dir != legacy_dir else []) + [legacy_dir]:
            try:
                client = chromadb.PersistentClient(path=str(base))
                collections = [c.name for c in client.list_collections()]
                report["findings"].append(f"Coleções em {base.name}: {len(collections)} ({', '.join(collections) or 'vazio'})")
                shown = True
            except Exception:
                continue
        if not shown:
            report["findings"].append("ChromaDB sem coleções legíveis.")
    except Exception as e:
        report["findings"].append(f"ChromaDB indisponível via binding ({type(e).__name__}) — fallback SQLite ativo.")

    return report


# ---------------------------------------------------------------------------
# 5. Guarda de SAÍDA — Tipagem TypeScript (Verification-First)
# ---------------------------------------------------------------------------
def check_tsc() -> dict:
    report = {"name": "tsc", "passed": True, "findings": []}
    try:
        res = subprocess.run(
            ["pnpm", "exec", "tsc", "--noEmit"], cwd=str(ROOT), capture_output=True, text=True,
            timeout=180, encoding="utf-8", errors="replace", shell=(os.name == "nt"),
        )
    except FileNotFoundError:
        report["findings"].append("pnpm/tsc não disponível no ambiente — verificação delegada ao CI.")
        return report

    if res.returncode == 0:
        report["findings"].append("TypeScript: 0 erros (pnpm exec tsc --noEmit).")
    else:
        report["passed"] = False
        errs = [l for l in res.stdout.splitlines() if "error TS" in l]
        report["findings"].append(f"TypeScript: {len(errs)} erro(s).")
        for l in errs[:8]:
            report["findings"].append(f"  {l.strip()[:140]}")
    return report


# ---------------------------------------------------------------------------
# Composição do gate
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Software Factory Guardrails — gate de entrada/saída dos agentes.")
    parser.add_argument("--handoff", action="store_true", help="Valida integridade do HANDOFF.md")
    parser.add_argument("--secrets", action="store_true", help="Varre secrets em código de produção")
    parser.add_argument("--spec", action="store_true", help="Audita SPECs com spec_linter")
    parser.add_argument("--rag", action="store_true", help="Verifica saúde do índice RAG")
    parser.add_argument("--tsc", action="store_true", help="Roda verificação de tipagem TypeScript")
    parser.add_argument("--all", action="store_true", help="Roda todas as guardas (gate composto)")
    parser.add_argument("--json", action="store_true", help="Saída em JSON estruturado")
    args = parser.parse_args()

    run_all = args.all or not any([args.handoff, args.secrets, args.spec, args.rag, args.tsc])

    guards = []
    if run_all or args.handoff:
        guards.append(check_handoff())
    if run_all or args.secrets:
        guards.append(check_secrets())
    if run_all or args.spec:
        guards.append(check_specs())
    if run_all or args.rag:
        guards.append(check_rag())
    if run_all or args.tsc:
        guards.append(check_tsc())

    gate_passed = all(g["passed"] for g in guards)

    if args.json:
        print(json.dumps({"gate_passed": gate_passed, "guards": guards}, indent=2, ensure_ascii=False))
        sys.exit(0 if gate_passed else 1)

    print(f"\n{SEPARATOR}")
    print("  🛡️  AGENT GUARDRAILS — SOFTWARE FACTORY GATE")
    print(SEPARATOR)
    for g in guards:
        icon = "✅" if g["passed"] else "❌"
        print(f"\n{icon} [{g['name'].upper()}]")
        for finding in g["findings"]:
            print(f"     • {finding}")
        if g.get("passes_note"):
            print(f"     ℹ️   {g['passes_note']}")
    print(SEPARATOR)
    if gate_passed:
        print("  🟢 GATE APROVADO — pronto para avançar na esteira.")
    else:
        print("  🔴 GATE REPROVADO — corrija as guardas falhas antes do handoff.")
    print(SEPARATOR + "\n")
    sys.exit(0 if gate_passed else 1)


if __name__ == "__main__":
    main()