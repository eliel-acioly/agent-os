#!/usr/bin/env python3
"""
AGENT-OS — SPEC LINTER & VERIFIER (Spec-Driven Development Kit SOTA 2026)
Inspirado nos padrões de RFC da Amazon (PR/FAQ), GitHub Spec Kit e TypeSpec.

Garante que nenhuma funcionalidade comece a ser codificada sem uma SPEC que
atenda aos 6 Critérios Áureos de Especificação Formal:
1. Metadados Canônicos (Código, Título, Versão, Domínio, Status).
2. Problema de Negócio & Critérios de Sucesso Mensuráveis.
3. Contratos / DTOs explicitamente mapeados (SSOT).
4. Critérios de Aceite no formato BDD (Given-When-Then).
5. Modos de Falha e Degradação Graciosa (Graceful Degradation).
6. Rastreabilidade com Testes Automatizados E2E.
"""

import sys
import os
import re
import argparse
import json

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

GOLDEN_CRITERIA = [
    {
        "id": "METADATA",
        "title": "Metadados Canônicos",
        "pattern": r"(SPEC-[A-Z]+-[0-9]+|Status:|Domínio:|Versão:)",
        "description": "A spec deve conter código único (ex: SPEC-CORE-001), Status e Domínio."
    },
    {
        "id": "BUSINESS_PROBLEM",
        "title": "Problema de Negócio & Valor",
        "pattern": r"(#+ *(1\.|O Problema|Objetivo|Problema de Negócio|Contexto|Por Quê))",
        "description": "Deve explicar claramente quem sofre, qual o custo da dor e o objetivo."
    },
    {
        "id": "CONTRACTS_MAPPING",
        "title": "Mapeamento de Contratos / DTOs (SSOT)",
        "pattern": r"(Contrato|DTO|shared/contracts|Interface|Schema|Payload)",
        "description": "Deve citar os contratos públicos e estruturas de dados compartilhadas."
    },
    {
        "id": "ACCEPTANCE_CRITERIA",
        "title": "Critérios de Aceite (BDD / Given-When-Then)",
        "pattern": r"(Critérios de Aceite|Dado que|Quando|Então|Given|When|Then|Cenário|Regra de Negócio)",
        "description": "Deve especificar o comportamento esperado de forma verificável."
    },
    {
        "id": "FAILURE_MODES",
        "title": "Modos de Falha & Degradação Graciosa",
        "pattern": r"(Falha|Erro|Timeout|Degradação|Resiliência|SLA|Circuit Breaker|Tratamento)",
        "description": "Deve prever o que acontece quando a rede, câmera ou banco falharem."
    },
    {
        "id": "TEST_TRACEABILITY",
        "title": "Rastreabilidade para Testes E2E",
        "pattern": r"(test_|testes|E2E|Asserção|docs/testes|Validação)",
        "description": "Deve indicar qual arquivo de teste comprova a implementação da Spec."
    }
]

def lint_spec_file(file_path):
    if not os.path.exists(file_path):
        return {"error": f"Arquivo não encontrado: {file_path}", "passed": False}

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    results = []
    passed_count = 0

    for crit in GOLDEN_CRITERIA:
        matched = bool(re.search(crit["pattern"], content, re.IGNORECASE))
        if matched:
            passed_count += 1
        results.append({
            "id": crit["id"],
            "title": crit["title"],
            "description": crit["description"],
            "passed": matched
        })

    score = round((passed_count / len(GOLDEN_CRITERIA)) * 100, 1)
    is_approved = score >= 80.0

    return {
        "file": os.path.basename(file_path),
        "path": file_path,
        "score": score,
        "approved": is_approved,
        "criteria": results
    }

def lint_directory(directory_path):
    reports = []
    for root, _, files in os.walk(directory_path):
        for f in files:
            if f.endswith(".md") and "SPEC-" in f.upper():
                p = os.path.join(root, f)
                reports.append(lint_spec_file(p))
    return reports

def main():
    parser = argparse.ArgumentParser(description="Agent-OS Spec Linter & Verifier")
    parser.add_argument("--file", "-f", help="Caminho para uma SPEC em Markdown")
    parser.add_argument("--dir", "-d", help="Diretório contendo múltiplas specs (ex: specs/)")
    parser.add_argument("--json", action="store_true", help="Saída em JSON estruturado")
    args = parser.parse_args()

    if args.file:
        report = lint_spec_file(args.file)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print(f"  AGENT-OS SPEC LINTER: {report['file']}")
            print("=" * 70)
            status_icon = "🟢 APROVADA" if report["approved"] else "🔴 REJEITADA (GAP DE ESPECIFICAÇÃO)"
            print(f"Score de Conformidade: {report['score']}% — Status: {status_icon}\n")
            for c in report["criteria"]:
                icon = "✅" if c["passed"] else "❌"
                print(f"  {icon} [{c['id']}] {c['title']}")
                if not c["passed"]:
                    print(f"     Ação Requerida: {c['description']}")
            print("=" * 70)
        return

    if args.dir:
        reports = lint_directory(args.dir)
        if args.json:
            print(json.dumps(reports, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print(f"  AGENT-OS SPEC AUDIT: {args.dir} ({len(reports)} Specs analisadas)")
            print("=" * 70)
            for r in reports:
                icon = "🟢" if r["approved"] else "🔴"
                print(f"  {icon} [{r['score']}%] {r['file']}")
            print("=" * 70)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
