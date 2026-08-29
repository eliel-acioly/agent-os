#!/usr/bin/env python3
"""
orchestrate_task.py — AntecipIA Agent Platform v2.0
Decompõe uma missão em tarefas atômicas e gera o HANDOFF.md preenchido.
Uso: python .agents/scripts/orchestrate_task.py --mission "Implementar módulo de alertas de pânico"
     python .agents/scripts/orchestrate_task.py --type full-stack --mission "Nova feature X"
     python .agents/scripts/orchestrate_task.py --status   (exibe status atual do HANDOFF.md)
"""

import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

SEPARATOR = "═" * 65
HANDOFF_FILE = Path("HANDOFF.md")

# Definição de esteiras por tipo de épico
PIPELINE_TEMPLATES = {
    "full-stack": {
        "description": "DB + API + UI + Realtime",
        "agents": ["Product", "Security", "DB", "Contracts", "API", "UI", "Logs", "Master"]
    },
    "backend-only": {
        "description": "Apenas endpoints e serviços backend, sem nova tela",
        "agents": ["Product", "API", "Logs", "Master"]
    },
    "frontend-only": {
        "description": "Apenas interface, endpoints existentes",
        "agents": ["Product", "UI", "Logs", "Master"]
    },
    "infra-vision": {
        "description": "Worker Python, gRPC, MediaMTX, modelos de IA",
        "agents": ["Product", "Gateway", "AI_Edge", "API", "Logs", "Master"]
    },
    "db-migration": {
        "description": "Schema, migrations e RLS",
        "agents": ["Product", "DB", "API", "Logs", "Master"]
    },
    "deploy": {
        "description": "Entrega em nuvem de feature já validada",
        "agents": ["Logs", "Master", "Deploy"]
    }
}

AGENT_TASK_HINTS = {
    "Product":      ["Definir Matriz 4V (POST/GET/PATCH/Event)", "Atualizar BACKLOG.md", "Criar briefing funcional para equipe técnica"],
    "Security":     ["Auditar rotas de acesso e RLS", "Verificar isolamento multi-tenant", "Validar sanitização de inputs"],
    "DB":           ["Criar/atualizar schema.ts com Drizzle ORM", "Gerar migration via drizzle-kit generate", "Criar políticas RLS para novas tabelas"],
    "Contracts":    ["Criar/atualizar interfaces em shared/contracts/", "Verificar sincronização de tipos Frontend↔Backend"],
    "Gateway":      ["Atualizar arquivo .proto se necessário", "Regenerar stubs Go", "Validar compilação com go build"],
    "API":          ["Criar rotas/controllers em server.ts", "Implementar validação Zod nos payloads", "Adicionar eventos Socket.IO se necessário"],
    "AI_Edge":      ["Atualizar pipeline de inferência em main.py", "Validar arquitetura híbrida vllm_factory.py", "Verificar ausência de PIL Image em loops críticos"],
    "UI":           ["Criar/atualizar componentes em antecipia-ui/src/", "Implementar estados: Loading/Empty/Error/Offline/Success", "Validar compilação tsc --noEmit"],
    "Logs":         ["Criar suíte de testes em /docs/testes/<data>/", "Executar npx --yes kill-port 3000", "Garantir 100% de assertions aprovadas"],
    "Master":       ["Executar validate_handoff_pipeline.py", "Executar pnpm tsc --noEmit", "Registrar épico em docs/04_HISTORICO_DO_PROJETO.md"],
    "Deploy":       ["Aplicar migrations no Supabase remoto", "Build e push de imagens Docker", "Deploy API no Railway e frontend em produção"]
}

def detect_epic_type(mission: str) -> str:
    """Heurística básica para detectar o tipo de épico pela missão."""
    m = mission.lower()
    if any(w in m for w in ["deploy", "produção", "release", "cloud", "entrega"]):
        return "deploy"
    if any(w in m for w in ["câmera", "visão", "yolo", "worker", "inference", "grpc", "rtsp", "streaming"]):
        return "infra-vision"
    if any(w in m for w in ["migration", "schema", "tabela", "banco", "rls", "postgres"]):
        return "db-migration"
    if any(w in m for w in ["tela", "interface", "dashboard", "ui", "painel", "componente"]):
        if not any(w in m for w in ["api", "endpoint", "rota", "backend"]):
            return "frontend-only"
    if any(w in m for w in ["endpoint", "api", "backend", "rota", "controller"]):
        if not any(w in m for w in ["tela", "interface", "dashboard", "ui"]):
            return "backend-only"
    return "full-stack"

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:50]

def generate_handoff(mission: str, epic_type: str, branch_name: str) -> str:
    template = PIPELINE_TEMPLATES[epic_type]
    agents = template["agents"]

    lines = [
        f"# AntecipIA - Sistema Tático de Hand-off",
        f"",
        f"> **Regra Suprema de Modificação:** APENAS O AGENTE EM TURNO PODE MODIFICAR SEU RESPECTIVO PASSO.",
        f"",
        f"**Épico Atual:** {mission}",
        f"**Tipo:** {epic_type.upper()} — {template['description']}",
        f"**Branch:** {branch_name}",
        f"**Gerado por:** @Orchestrator em {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"---",
        f""
    ]

    for i, agent in enumerate(agents, 1):
        hints = AGENT_TASK_HINTS.get(agent, ["Executar tarefa conforme skill."])
        lines.append(f"## {i}. Passo {i} (@{agent})")
        lines.append(f"**Responsável:** @{agent}")
        lines.append(f"**Status:** AGUARDANDO")
        for hint in hints:
            lines.append(f"- [ ] {hint}")
        lines.append("")

    return "\n".join(lines)

def show_status():
    """Exibe o status atual do HANDOFF.md."""
    if not HANDOFF_FILE.exists():
        print("[AVISO] HANDOFF.md não encontrado.")
        return

    content = HANDOFF_FILE.read_text(encoding="utf-8")
    print(f"\n{SEPARATOR}")
    print("  📋 STATUS DO HANDOFF.md ATUAL")
    print(SEPARATOR)

    # Extrair passos
    steps = re.findall(r"## \d+\. Passo \d+ \((@\w+)\).*?\*\*Status:\*\* ([^\n]+)", content, re.DOTALL)
    for agent, status in steps:
        icon = "✅" if "CONCLU" in status.upper() or "PASS" in status.upper() else ("🔄" if "PROGRESSO" in status.upper() else "⏳")
        print(f"  {icon} {agent}: {status.strip()}")

    unchecked = content.count("- [ ]")
    checked = content.count("- [x]")
    total = unchecked + checked
    print(f"\n  Progresso: {checked}/{total} tarefas concluídas")
    print(SEPARATOR + "\n")

def main():
    parser = argparse.ArgumentParser(description="Orquestra tarefas e gera HANDOFF.md.")
    parser.add_argument("--mission", "-m", help="Descrição da missão/épico")
    parser.add_argument("--type", "-t", choices=list(PIPELINE_TEMPLATES.keys()),
                        help="Tipo de épico (auto-detectado se omitido)")
    parser.add_argument("--status", "-s", action="store_true", help="Exibe o status atual do HANDOFF.md")
    parser.add_argument("--branch", "-b", help="Nome da branch (gerado automaticamente se omitido)")
    args = parser.parse_args()

    if args.status:
        show_status()
        sys.exit(0)

    if not args.mission:
        parser.print_help()
        sys.exit(1)

    mission = args.mission.strip()
    epic_type = args.type or detect_epic_type(mission)
    branch_name = args.branch or f"feature/{slugify(mission)[:40]}"

    print(f"\n{SEPARATOR}")
    print(f"  🎯 @Orchestrator — Decomposição de Missão")
    print(SEPARATOR)
    print(f"  Missão: {mission}")
    print(f"  Tipo detectado: {epic_type.upper()}")
    print(f"  Branch: {branch_name}")
    print(f"  Esteira: {' ➔ '.join(PIPELINE_TEMPLATES[epic_type]['agents'])}")
    print(SEPARATOR)

    handoff_content = generate_handoff(mission, epic_type, branch_name)

    if HANDOFF_FILE.exists():
        backup = Path(f"HANDOFF.backup.{datetime.now().strftime('%H%M%S')}.md")
        backup.write_text(HANDOFF_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\n[INFO] HANDOFF.md anterior salvo em: {backup}")

    HANDOFF_FILE.write_text(handoff_content, encoding="utf-8")
    print(f"[OK] HANDOFF.md gerado com sucesso para o épico: {mission}")
    print(f"\n📋 Próximo agente a assumir: @{PIPELINE_TEMPLATES[epic_type]['agents'][0]}")
    print(f"   Execute: git checkout -b {branch_name}\n")

if __name__ == "__main__":
    main()
