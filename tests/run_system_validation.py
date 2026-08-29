#!/usr/bin/env python3
"""
AGENT-OS — SUÍTE DE TESTES E VALIDAÇÃO DE SISTEMA
Executa uma bateria rigorosa de verificação funcional em todos os motores,
skills e ferramentas do repositório para garantir conformidade estrita.
"""

import sys
import os
import subprocess
import json
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(ROOT_DIR, "scripts")
SKILLS_DIR = os.path.join(ROOT_DIR, "skills")

def run_step(step_name, command, expected_exit_code=0):
    print(f"\n[TESTE] {step_name}")
    print(f"Comando: {' '.join(command)}")
    start = time.time()
    res = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = round((time.time() - start) * 1000, 2)

    passed = (res.returncode == expected_exit_code)
    status = "✅ PASS" if passed else f"❌ FAIL (Exit {res.returncode})"
    print(f"Resultado: {status} ({elapsed}ms)")
    if not passed:
        print("STDERR:", res.stderr.strip()[:300])
        print("STDOUT:", res.stdout.strip()[:300])
    return passed, res.stdout

def main():
    print("=" * 75)
    print("  🧪 AGENT-OS: INICIANDO SUÍTE FORMAL DE VALIDAÇÃO DE SISTEMA")
    print("=" * 75)
    print(f"Raiz do Repositório: {ROOT_DIR}")

    total_tests = 0
    passed_tests = 0

    # 1. Validação de Skills
    total_tests += 1
    skill_dirs = [d for d in os.listdir(SKILLS_DIR) if os.path.isdir(os.path.join(SKILLS_DIR, d))]
    valid_skills = 0
    for s in skill_dirs:
        skill_file = os.path.join(SKILLS_DIR, s, "SKILL.md")
        if os.path.exists(skill_file):
            valid_skills += 1
    if valid_skills >= 18:
        print(f"\n[TESTE] Verificação Estrutural de Skills ({valid_skills}/18 encontradas)")
        print("Resultado: ✅ PASS (Todas as skills canônicas presentes)")
        passed_tests += 1
    else:
        print(f"\n[TESTE] Verificação Estrutural de Skills ({valid_skills}/18)")
        print("Resultado: ❌ FAIL (Faltam skills no diretório)")

    # 2. Teste do spec_linter.py em Spec Válida
    total_tests += 1
    sample_spec = os.path.join(ROOT_DIR, "examples", "ClinicReactivator", "docs", "specs", "SPEC-CORE-001-motor-central.md")
    p, out = run_step("Spec Linter: Avaliação de Spec Formal Aprovada", [sys.executable, os.path.join(SCRIPTS_DIR, "spec_linter.py"), "--file", sample_spec])
    if p and "APROVADA" in out:
        passed_tests += 1

    # 3. Teste do repo_map_engine.py
    total_tests += 1
    p, out = run_step("Repo Map Engine: Mapeamento Topológico de Centralidade", [sys.executable, os.path.join(SCRIPTS_DIR, "repo_map_engine.py"), "--dir", ROOT_DIR, "--top", "5"])
    if p and ("HUB CENTRAL" in out or "Mapeados" in out):
        passed_tests += 1

    # 4. Teste do scientific_researcher.py (Cenário Válido)
    total_tests += 1
    p, out = run_step("Scientific Researcher: Hipótese Falsificável e Quantitativa", [
        sys.executable, os.path.join(SCRIPTS_DIR, "scientific_researcher.py"),
        "-t", "Benchmark de Conexões",
        "-hyp", "Pool de conexões reduz latência p99 para menos de 25ms",
        "-m", "Latencia p99 < 25ms",
        "-r", "LOW"
    ])
    if p and "HIPÓTESE VALIDADA" in out:
        passed_tests += 1

    # 5. Teste do scientific_researcher.py (Rejeição de Proposta Sem Métrica)
    total_tests += 1
    p, out = run_step("Scientific Researcher: Rejeição Epistêmica de Hype sem Métrica", [
        sys.executable, os.path.join(SCRIPTS_DIR, "scientific_researcher.py"),
        "-t", "Modismo Tecnológico",
        "-hyp", "Trocar biblioteca estável por novidade",
        "-m", "Fica mais bonito",
        "-r", "HIGH"
    ])
    if p and "HIPÓTESE REJEITADA" in out:
        passed_tests += 1

    # 6. Teste E2E de Exemplo Gerado
    total_tests += 1
    test_file = os.path.join(ROOT_DIR, "examples", "ClinicReactivator", "tests", "test_core_e2e.js")
    p, out = run_step("Execução do Teste E2E da Venture de Exemplo", ["node", test_file])
    if p and "100% dos testes aprovados" in out:
        passed_tests += 1

    print("\n" + "=" * 75)
    print(f"  RESULTADO DA SUÍTE: {passed_tests}/{total_tests} TESTES APROVADOS ({round((passed_tests/total_tests)*100, 1)}%)")
    print("=" * 75)

    if passed_tests == total_tests:
        print("🟢 SISTEMA TOTALMENTE VERIFICADO E EM CONFORMIDADE OPERACIONAL.")
        sys.exit(0)
    else:
        print("🔴 FALHAS DETECTADAS NA SUÍTE DE TESTES.")
        sys.exit(1)

if __name__ == "__main__":
    main()
