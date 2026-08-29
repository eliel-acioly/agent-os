#!/usr/bin/env python3
"""
AGENT-OS — BOOTSTRAP DE NOVO PROJETO (SOTA 2026)
Permite instanciar a plataforma de agentes agnóstica em qualquer novo repositório
(Node, Rust, Go, Python, Tauri, etc.) em menos de 5 segundos.

Uso:
    python .agents/scripts/bootstrap_project.py --target-dir /caminho/do/novo/projeto --name "MindAtlas" --domain "DESKTOP_OS"
"""

import sys
import os
import argparse
import shutil

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CONSTITUTION_TEMPLATE = """# CONSTITUIÇÃO SOBERANA DO PROJETO: {project_name}
> Versão: 1.0 — Governança Canônica Spec-Driven (Aerospace Standard SOTA 2026)

## 1. IDENTIDADE FUNDAMENTAL
- O que este projeto É: {domain_description}
- O que este projeto NÃO É: Não desviar da proposta central.

## 2. A HIERARQUIA CANÔNICA SUPREMA (11 ELOS)
IDENTIDADE → CONSTITUIÇÃO → ONTOLOGIA → ARQUITETURA → SPECS → ADRs → CONTRATOS → GRAFO → AGENTES → CÓDIGO → TESTES

## 3. AS 4 LEIS DO SOTA 2026
1. Repository-Awareness: Proibido adivinhar contexto. Use sempre GraphRAG e AST antes de propor código.
2. Bounded Autonomy: Cada agente atua estritamente em sua jurisdição.
3. Reflection & PRAR Loop: Proibido entregar código sem testes automatizados locais.
4. Grounding Rígido: Proibido inventar classes ou contratos inexistentes no grafo.
"""

HANDOFF_TEMPLATE = """# HANDOFF OPERACIONAL — {project_name} v1.0

## 🚀 Tarefa Ativa: BOOTSTRAP INICIAL CONCLUÍDO
**Agente:** @Orchestrator (Guardião da Execução da Intenção)  
**Status Global:** 🟢 **PROJETO INICIALIZADO COM SUCESSO SOB A PLATAFORMA AGENT-OS**  
**Próximo Passo:** @Product define os épicos iniciais e a SPEC de fundação em docs/specs/.
"""

def bootstrap_project(target_dir, project_name, domain):
    target_path = os.path.abspath(target_dir)
    print("=" * 70)
    print(f"  AGENT-OS BOOTSTRAPPER: INICIALIZANDO {project_name.upper()}")
    print("=" * 70)
    print(f"📁 Diretório Alvo: {target_path}")
    print(f"🏷️ Domínio do Sistema: {domain}\n")

    os.makedirs(os.path.join(target_path, "docs", "specs"), exist_ok=True)
    os.makedirs(os.path.join(target_path, "docs", "adr"), exist_ok=True)
    os.makedirs(os.path.join(target_path, "docs", "testes"), exist_ok=True)
    os.makedirs(os.path.join(target_path, "shared", "contracts"), exist_ok=True)

    # 1. Cria a Constituição
    const_path = os.path.join(target_path, "docs", "00_CONSTITUICAO.md")
    if not os.path.exists(const_path):
        with open(const_path, "w", encoding="utf-8") as f:
            f.write(CONSTITUTION_TEMPLATE.format(
                project_name=project_name,
                domain_description=f"Sistema especializado no domínio {domain} construído sob rigor de engenharia autônoma."
            ))
        print("  ✅ docs/00_CONSTITUICAO.md criado.")

    # 2. Cria o HANDOFF inicial
    handoff_path = os.path.join(target_path, "HANDOFF.md")
    if not os.path.exists(handoff_path):
        with open(handoff_path, "w", encoding="utf-8") as f:
            f.write(HANDOFF_TEMPLATE.format(project_name=project_name))
        print("  ✅ HANDOFF.md inicializado.")

    print("\n🎉 Bootstrap finalizado com sucesso!")
    print("O projeto agora possui estrutura Spec-Driven, governança de agentes e diretórios canônicos prontos.")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Agent-OS Project Bootstrapper")
    parser.add_argument("--target-dir", "-t", required=True, help="Diretório raiz do novo projeto")
    parser.add_argument("--name", "-n", default="NovoProjeto", help="Nome do projeto")
    parser.add_argument("--domain", "-d", default="GENERAL_SOFTWARE", help="Domínio do sistema")
    args = parser.parse_args()

    bootstrap_project(args.target_dir, args.name, args.domain)

if __name__ == "__main__":
    main()
