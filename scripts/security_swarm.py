#!/usr/bin/env python3
"""
security_swarm.py — Varredura de Vulnerabilidades validada + plano de remediação (agnóstico a projeto)
Executa um "enxame" estático sobre o PROJETO LINKADO procurando vetores de exploração:
  - Secrets em código de produção
  - Rotas Next.js mutantes sem autenticação explícita
  - XSS (dangerouslySetInnerHTML)
  - RLS com risco / abuse (using(true), service_role no cliente)
  - Chaves públicas sensíveis / 'use client' com server-only
Cada achado é classificado (LOW/MED/HIGH) e consolidado em
docs/SECURITY_SWARM_REPORT.md do projeto linkado.
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
try:
    from project_context import get_project_root
    PROJECT_ROOT = get_project_root()
except Exception:
    PROJECT_ROOT = Path.cwd()

ROOT = PROJECT_ROOT
REPORT_DIR = ROOT / "docs"
REPORT_FILE = REPORT_DIR / "SECURITY_SWARM_REPORT.md"
SKIP_DIRS = {"node_modules", ".next", ".git", "dist", "build", "__pycache__", ".agents", "docs", ".vercel", ".github"}
TARGET_DIRS = ["app", "lib", "components", "scripts"]
VALID_EXTS = (".ts", ".tsx", ".js", ".jsx", ".py")
SEP = "=" * 70


def scan_files():
    for d in TARGET_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [x for x in dns if x not in SKIP_DIRS]
            for fn in fns:
                if not fn.endswith(VALID_EXTS):
                    continue
                fp = Path(dp) / fn
                rel = fp.relative_to(ROOT).as_posix()
                try:
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for line_no, line in enumerate(text.splitlines(), 1):
                    yield rel, line_no, line, text


def detect(rel, line_no, line, content):
    hits = []
    low = line.lower()

    # 1. Secrets inline (não-interpolação)
    if re.search(r"SUPABASE_SERVICE_ROLE_KEY\s*[=:]\s*[\"'][a-zA-Z0-9_-]{20,}", line, re.I) and "${" not in line:
        hits.append(("SECRETS", "HIGH", "Service Role Key inline em código"))
    if re.search(r"\bsk-[A-Za-z0-9_-]{20,}\b", line):
        hits.append(("SECRETS", "HIGH", "API key OpenAI inline"))

    # 2. XSS em React
    if "dangerouslySetInnerHTML" in line:
        hits.append(("XSS", "MED", "dangerouslySetInnerHTML — risco de XSS se o conteúdo não for sanitizado"))

    # 3. RLS arriscado
    if "for update using (true)" in low or re.search(r"policy.*using\s*\(\s*true\s*\)", line, re.I):
        hits.append(("RLS", "HIGH", "Política RLS com using(true) — expõe todos os registros"))

    # 4. service_role no lado cliente
    if "SERVICE_ROLE" in line and ("'use client'" in content or "NEXT_PUBLIC" in line):
        hits.append(("EXPOSURE", "HIGH", "Service Role presente em arquivo client-side"))

    # 5. Rota mutante sem auth (heurística)
    if "/route.ts" in rel and "export async function POST" in line:
        hits.append(("AUTH_REVIEW", "MED", "Rota POST — revisar guarda de autenticação (getAuthenticatedUser)"))

    # 6. eval / exec
    if re.search(r"\b(eval|new Function)\(|child_process\.exec\(", line):
        hits.append(("INJECTION", "HIGH" if "exec" in low else "MED", "execução dinâmica de código"))

    # 7. Query SQL concatenada
    if re.search(r"from\s*\(\s*`|\.from\(\s*`", line, re.I):
        hits.append(("SQLI", "MED", "possível concatenação de SQL dinâmico"))

    return hits


def main():
    p = argparse.ArgumentParser(description="security_swarm — varredura de vulnerabilidades validada.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-report", action="store_true", help="Não grava o relatório md")
    args = p.parse_args()

    findings = []
    for rel, line_no, line, content in scan_files():
        for cat, sev, desc in detect(rel, line_no, line, content):
            findings.append({
                "file": rel, "line": line_no, "category": cat,
                "severity": sev, "description": desc,
                "snippet": line.strip()[:140],
            })

    by_cat = {}
    for f in findings:
        by_cat.setdefault(f["category"], []).append(f)

    if args.json:
        print(json.dumps({
            "total": len(findings),
            "byCategory": {k: len(v) for k, v in by_cat.items()},
            "findings": findings,
        }, indent=2, ensure_ascii=False))
        return

    print(SEP)
    print("  🛡️ SECURITY SWARM — varredura de vulnerabilidades")
    print(SEP)
    if not findings:
        print("  🟢 Nenhuma vulnerabilidade detectada pelo enxame estático.")
        print(SEP + "\n")
        return
    for cat, items in sorted(by_cat.items()):
        highs = sum(1 for i in items if i["severity"] == "HIGH")
        print(f"\n  [{cat}] {len(items)} ocorrência(s) ({highs} HIGH)")
        for i in items[:12]:
            print(f"     • [{i['severity']:>4}] {i['file']}:{i['line']}  {i['description'][:80]}")
            if i["severity"] == "HIGH":
                print(f"           {i['snippet'][:100]}")
    print(SEP)

    if not args.no_report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(f"# SECURITY SWARM REPORT (Devin Security Swarm-style)\n\n")
            f.write(f"> Gerado automaticamente em {datetime.now().isoformat()}\n")
            f.write(f"> Autoridade: @Security (enxame estático) | Verificação: runtime pendente\n\n")
            f.write(f"## Resumo\n\n- **Total de achados:** {len(findings)}\n")
            f.write(f"- **Críticos (HIGH):** {sum(1 for x in findings if x['severity']=='HIGH')}\n")
            f.write(f"- **Médios (MED):** {sum(1 for x in findings if x['severity']=='MED')}\n")
            f.write(f"\n## Detalhamento por categoria\n\n")
            for cat, items in sorted(by_cat.items()):
                f.write(f"### {cat}\n\n")
                f.write("| Severidade | Arquivo | Linha | Descrição |\n|---|---|---|---|\n")
                for i in items:
                    f.write(f"| {i['severity']} | `{i['file']}` | {i['line']} | {i['description']} |\n")
                f.write("\n")
            f.write("## Plano de Remediação (PR sugerido)\n\n")
            f.write("1. Trocar qualquer secret inline por `process.env.*` (nunca commitar valores fixos).\n")
            f.write("2. Revisar rotas POST sem guarda: `getAuthenticatedUser(req)` antes de mutação.\n")
            f.write("3. Substituir `dangerouslySetInnerHTML` por componentes sanitizados (DOMPurify) ou remover.\n")
            f.write("4. Auditar políticas RLS: eliminar `using(true)` e reduzir escopo por tenant.\n")
            f.write("5. Rodar o enxame novamente até zerar HIGH/MED antes do próximo deploy.\n")
        print(f"\n  📁 Relatório gerado: {REPORT_FILE}")
    print(SEP + "\n")


if __name__ == "__main__":
    main()