#!/usr/bin/env python3
"""
check_qa_matrix.py
Script de Auditoria Autônoma executado pelo @Logs.
Verifica a integridade da suíte de testes, estrutura de diretórios e conformidade com a governança.
"""

import sys
import json
from pathlib import Path

# Configurar encoding seguro para console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def check_qa_matrix():
    print("[AUDITORIA] Auditoria Autônoma de QA e Observabilidade (@Logs)...")
    errors = 0

    # 1. Verificar diretório canônico de testes
    docs_testes = Path("docs/testes")
    if not docs_testes.exists():
        print("[ERRO] Diretório canônico docs/testes/ não encontrado!")
        errors += 1
    else:
        subfolders = [f for f in docs_testes.iterdir() if f.is_dir()]
        print(f"[INFO] Subpastas de testes datados em /docs/testes/ ({len(subfolders)} encontradas):")
        total_test_files = 0
        for folder in subfolders:
            test_files = list(folder.glob("*.ts")) + list(folder.glob("*.js")) + list(folder.glob("*.py"))
            total_test_files += len(test_files)
            print(f"   - {folder.name} ({len(test_files)} scripts de teste)")
        print(f"[INFO] Total de scripts executáveis de teste: {total_test_files}")

    # 2. Verificar se há pastas ilegais de teste dispersas no projeto
    illegal_dirs = [
        Path("antecipia-api/tests"),
        Path("antecipia-api/__tests__"),
        Path("antecipia-api/src/tests"),
        Path("antecipia-ui/tests"),
        Path("antecipia-ui/__tests__"),
        Path("antecipia-ui/src/tests"),
    ]

    found_illegal = False
    for p in illegal_dirs:
        if p.exists():
            print(f"[VIOLAÇÃO DE GOVERNANÇA] Pasta de teste ilegal encontrada: {p}")
            found_illegal = True
            errors += 1

    if not found_illegal:
        print("[OK] Nenhuma pasta de teste dispersa encontrada fora de /docs/testes/ (Zero Duplicação).")

    # 3. Verificar scripts de teste no package.json da API
    api_pkg = Path("antecipia-api/package.json")
    if api_pkg.exists():
        try:
            data = json.loads(api_pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            print("\n[INFO] Mapeamento de Testes no antecipia-api/package.json:")
            
            test_commands = [k for k in scripts.keys() if k.startswith("test")]
            for cmd in test_commands:
                target = scripts[cmd]
                valid_target = "docs/testes" in target or "tsx" in target or "ts-node" in target
                icon = "[OK]" if valid_target else "[AVISO]"
                print(f"   {icon} npm run {cmd} -> {target}")

            if "test:panic" not in scripts:
                print("   [AVISO] 'test:panic' não configurado no package.json.")
        except Exception as e:
            print(f"[ERRO] Falha ao inspecionar antecipia-api/package.json: {e}")
            errors += 1

    if errors > 0:
        print(f"\n[FALHA] Auditoria de QA encontrou {errors} inconsistências que exigem atenção.")
        sys.exit(1)
    else:
        print("\n[OK] AUDITORIA DE QA CONCLUÍDA COM SUCESSO: Estrutura 100% aderente às diretrizes.")
        sys.exit(0)

if __name__ == "__main__":
    check_qa_matrix()
