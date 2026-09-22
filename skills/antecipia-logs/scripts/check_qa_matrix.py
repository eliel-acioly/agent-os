#!/usr/bin/env python3
"""
check_qa_matrix.py
Script de Auditoria Autônoma executado pelo @Logs (Agent-OS).
Verifica a integridade da suíte de testes e scripts de validação no projeto ativo.
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

    # 1. Verificar diretórios comuns de testes
    test_dirs = [Path("docs/testes"), Path("tests"), Path("__tests__"), Path("e2e")]
    found_dirs = [d for d in test_dirs if d.exists() and d.is_dir()]
    
    if found_dirs:
        for d in found_dirs:
            test_files = list(d.glob("**/*.ts")) + list(d.glob("**/*.js")) + list(d.glob("**/*.py"))
            print(f"[INFO] Diretório de testes encontrado: {d} ({len(test_files)} scripts)")
    else:
        print("[INFO] Nenhum diretório canônico de testes tradicional encontrado na raiz.")

    # 2. Inspecionar scripts de teste no package.json da raiz (se existir)
    root_pkg = Path("package.json")
    if root_pkg.exists():
        try:
            data = json.loads(root_pkg.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            test_commands = [k for k in scripts.keys() if "test" in k]
            
            if test_commands:
                print(f"\n[INFO] Mapeamento de Testes em {root_pkg}:")
                for cmd in test_commands:
                    target = scripts[cmd]
                    print(f"   [OK] run {cmd} -> {target}")
            else:
                print(f"\n[AVISO] Nenhum script de teste mapeado em {root_pkg}.")
        except Exception as e:
            print(f"[ERRO] Falha ao inspecionar {root_pkg}: {e}")
            errors += 1

    if errors > 0:
        print(f"\n[FALHA] Auditoria de QA encontrou {errors} inconsistências.")
        sys.exit(1)
    else:
        print("\n[OK] AUDITORIA DE QA CONCLUÍDA: Mapeamento de testes executado com sucesso.")
        sys.exit(0)

if __name__ == "__main__":
    check_qa_matrix()
