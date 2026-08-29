#!/usr/bin/env python3
"""
validate_handoff_pipeline.py
Script de Auditoria Autônoma executado pelo @Master.
Valida se o HANDOFF.md respeita a lei do pipeline estreito com todas as 12 personas do AntecipIA:
@Orchestrator -> (F1: @Product -> @Security) -> (F2: @DB -> @Gateway) -> (F3: @Contracts -> @API -> @AI_Edge) -> (F4: @UI) -> (F5: @Logs) -> (F6: @Master) -> (F7: @Deploy)
"""

import sys
import re
from pathlib import Path

# Configurar encoding seguro para console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Mapa de estágios da esteira canônica (com suporte a aliases)
PIPELINE_STAGES = {
    # Fase 0: Orquestração e Decomposição
    "orchestrator": 0,
    "antecipia-orchestrator": 0,
    "antecipia_orchestrator": 0,

    # Fase 1: Concepção & Segurança
    "product": 1,
    "antecipia-product": 1,
    "antecipia_product": 1,
    "security": 1,
    "antecipia-security": 1,
    "antecipia_security": 1,

    # Fase 2: Persistência & Streaming
    "db": 2,
    "antecipia-db": 2,
    "antecipia_db": 2,
    "gateway": 2,
    "antecipia-gateway": 2,
    "antecipia_gateway": 2,

    # Fase 3: Contratos, Backend & Borda IA
    "contracts": 3,
    "antecipia-contracts": 3,
    "antecipia_contracts": 3,
    "api": 3,
    "antecipia-api": 3,
    "antecipia_api": 3,
    "ai_edge": 3,
    "ai-edge": 3,
    "aiedge": 3,
    "antecipia-ai-edge": 3,
    "antecipia_ai_edge": 3,

    # Fase 4: Experiência & Interface
    "ui": 4,
    "antecipia-ui": 4,
    "antecipia_ui": 4,

    # Fase 5: QA & Observabilidade (Barreira Obrigatória)
    "logs": 5,
    "antecipia-logs": 5,
    "antecipia_logs": 5,

    # Fase 6: Gatekeeper & Merge (Aprovação Final)
    "master": 6,
    "antecipia-master": 6,
    "antecipia_master": 6,

    # Fase 7: Cloud Delivery (Entrega em Produção)
    "deploy": 7,
    "antecipia-deploy": 7,
    "antecipia_deploy": 7
}

def normalize_agent_name(name: str) -> str:
    """Normaliza o identificador do agente para comparação padronizada."""
    clean = re.sub(r"^[/@]+", "", name).strip().lower()
    return clean

def validate_handoff(handoff_path: str = "HANDOFF.md"):
    path = Path(handoff_path)
    if not path.exists():
        print(f"[ERRO CRÍTICO] {handoff_path} não encontrado no diretório atual.")
        sys.exit(1)

    content = path.read_text(encoding="utf-8")
    print(f"[AUDITORIA] Auditoria de Handoff Iniciada para: {path.resolve()}")
    print("-" * 65)

    # Extrair Passos do HANDOFF
    # Padrão: ## N. Passo X (@Agente) ou **Passo X ... (@Agente)**
    step_blocks = re.findall(r"(?:##\s*\d+\.\s*Passo\s*\d+\s*\(([@/A-Za-z0-9_-]+)\)|(?:\*\*Passo\s*\d+:[^*]+\(Para\s*`?([@/A-Za-z0-9_-]+)`?\)\*\*))", content)
    
    agent_sequence = []
    for step in step_blocks:
        agent_raw = step[0] if step[0] else step[1]
        agent_clean = normalize_agent_name(agent_raw)
        if agent_clean:
            agent_sequence.append(agent_clean)

    if not agent_sequence:
        print("[AVISO] Nenhum passo de agente explícito encontrado no HANDOFF.md.")
        sys.exit(0)

    display_sequence = ["@" + a.replace("antecipia-", "").replace("antecipia_", "").upper() for a in agent_sequence]
    print(f"[ESTEIRA DETECTADA] {' ➔ '.join(display_sequence)}")

    # Validar ordem relativa dos agentes conhecidos
    current_stage = 0
    stage_violations = []

    for agent in agent_sequence:
        stage = PIPELINE_STAGES.get(agent, None)
        if stage is not None:
            if stage < current_stage:
                if agent in ["logs", "antecipia-logs", "master", "antecipia-master"]:
                    stage_violations.append(f"Agente @{agent} (Estágio {stage}) foi posicionado antes do esperado.")
            current_stage = max(current_stage, stage)

    # Validação Crítica: Precedência do Master
    master_keys = ["master", "antecipia-master", "antecipia_master"]
    logs_keys = ["logs", "antecipia-logs", "antecipia_logs"]
    
    for m_key in master_keys:
        if m_key in agent_sequence:
            master_idx = agent_sequence.index(m_key)
            if master_idx > 0:
                previous_agent = agent_sequence[master_idx - 1]
                if previous_agent not in logs_keys:
                    print("\n[VIOLAÇÃO DE PIPELINE DETECTADA]")
                    print(f"[ERRO] O @Master foi posicionado após @{previous_agent} sem a validação mandatória de testes do @Logs!")
                    print("[BLOQUEIO] MERGE BLOQUEADO PELO MASTER. O Handoff deve obrigatoriamente incluir o @Logs antes do @Master.")
                    sys.exit(2)
                else:
                    print(f"[OK] Precedência mandatória validada: @{previous_agent} ➔ @Master.")

    # Validação de Dependência de Banco (@DB antes de @API se ambos existirem)
    db_indices = [agent_sequence.index(k) for k in ["db", "antecipia-db"] if k in agent_sequence]
    api_indices = [agent_sequence.index(k) for k in ["api", "antecipia-api"] if k in agent_sequence]
    if db_indices and api_indices:
        if min(db_indices) > min(api_indices):
            print("[AVISO] @DB posicionado após @API. Recomenda-se que migrations precedam o desenvolvimento de rotas.")
        else:
            print("[OK] Precedência de persistência: @DB ➔ @API.")

    # Verificar se os testes do @Logs foram executados e marcados quando @Logs estiver presente
    if any(k in agent_sequence for k in logs_keys):
        logs_step = re.search(r"## \d+\. Passo \d+ \((?:@Logs|@antecipia-logs)\)[\s\S]*?(?:\*\*Status:\*\*|Status:)\s*([^\n\r]+)", content, re.IGNORECASE)
        if logs_step:
            logs_status = logs_step.group(1).strip()
            print(f"[INFO] Status do @Logs: {logs_status}")
            if "CONCLU" not in logs_status.upper() and "PASS" not in logs_status.upper():
                print("\n[VIOLAÇÃO DE QUALIDADE]")
                print(f"[ERRO] O @Logs ainda não concluiu a suíte de testes com sucesso (Status: {logs_status}).")
                sys.exit(3)
            else:
                print("[OK] @Logs confirmou aprovação de testes E2E/QA.")

    print("-" * 65)
    print("[OK] VALIDAÇÃO DO PIPELINE CONCLUÍDA: Handoff está em conformidade com o ecossistema de agentes.")
    sys.exit(0)

if __name__ == "__main__":
    validate_handoff()
