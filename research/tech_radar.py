#!/usr/bin/env python3
"""
tech_radar.py — AntecipIA Aerospace-Grade Agent Platform v3.0
Mapeador e Radar Tecnológico do Ecossistema AntecipIA.
Classifica tecnologias em 4 anéis: ADOPT, TRIAL, ASSESS, HOLD.
Uso: python .agents/research/tech_radar.py [--export-json] [--quadrant QUALQUER]
"""

import sys
import json
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

AGENTS_DIR = Path(__file__).parent.parent
ROOT = AGENTS_DIR.parent
RADAR_DATA_FILE = AGENTS_DIR / "research" / "tech_radar.json"

SEPARATOR = "═" * 70

# ─────────────────────────────────────────────────────────────────────────────
# Base de Conhecimento do Tech Radar AntecipIA
# ─────────────────────────────────────────────────────────────────────────────

RADAR_QUADRANTS = {
    "techniques": "Técnicas, Padrões & Algoritmos",
    "platforms":  "Plataformas, Infraestrutura & Cloud",
    "tools":      "Ferramentas de Engenharia & Harness",
    "frameworks": "Linguagens, Frameworks & Bibliotecas"
}

RADAR_RINGS = {
    "ADOPT":  "🟢 ADOPT  — Padrão obrigatório comprovado em produção",
    "TRIAL":  "🟡 TRIAL  — Em experimentação avançada em novos módulos",
    "ASSESS": "🔵 ASSESS — Em pesquisa e prototipagem exploratória",
    "HOLD":   "🔴 HOLD   — Proibido / Descontinuado / Anti-padrão"
}

TECH_REGISTRY = [
    # ── TECHNIQUES ──
    {
        "name": "Evidential Deep Learning (EDL)",
        "quadrant": "techniques", "ring": "ADOPT",
        "agent": "AI_Edge",
        "description": "Distribuição Dirichlet pós-YOLO para quantificação de incerteza epistêmica/aleatória."
    },
    {
        "name": "Conformal Prediction (Split Conformal)",
        "quadrant": "techniques", "ring": "TRIAL",
        "agent": "AI_Edge",
        "description": "Garantia matemática de conjuntos de predição com nível de erro delimitado (1 - α)."
    },
    {
        "name": "Contract-First Architecture (SSOT)",
        "quadrant": "techniques", "ring": "ADOPT",
        "agent": "Contracts",
        "description": "shared/contracts/ como fonte única da verdade para todos os DTOs e eventos."
    },
    {
        "name": "Circuit Breaker & Graceful Degradation",
        "quadrant": "techniques", "ring": "ADOPT",
        "agent": "API",
        "description": "Isolamento de falhas em cascata com fallbacks determinísticos."
    },
    {
        "name": "Expand/Contract Zero-Downtime Migrations",
        "quadrant": "techniques", "ring": "ADOPT",
        "agent": "DB",
        "description": "Evolução de schema suportando versões N e N-1 simultaneamente."
    },
    {
        "name": "Statecharts / Finite State Machines (FSM)",
        "quadrant": "techniques", "ring": "TRIAL",
        "agent": "UI",
        "description": "Modelagem formal de estados de tela eliminando estados impossíveis em COPOM."
    },
    {
        "name": "Property-Based Testing (Invariant Fuzzing)",
        "quadrant": "techniques", "ring": "ADOPT",
        "agent": "Logs",
        "description": "Geração randômica de centenas de casos de teste validando invariantes universais."
    },
    {
        "name": "PIL Image in Hot Video Loops",
        "quadrant": "techniques", "ring": "HOLD",
        "agent": "AI_Edge",
        "description": "Anti-padrão: conversões PIL Image no Python causam memory leak e timeout."
    },
    {
        "name": "Ad-Hoc Local Types in Frontend/Backend",
        "quadrant": "techniques", "ring": "HOLD",
        "agent": "Contracts",
        "description": "Anti-padrão: tipos não exportados em shared/contracts/ causam dessincronização."
    },

    # ── PLATFORMS ──
    {
        "name": "ChromaDB (Vector Store RAG)",
        "quadrant": "platforms", "ring": "ADOPT",
        "agent": "Orchestrator",
        "description": "Indexação vetorial local de código para recuperação semântica eficiente."
    },
    {
        "name": "Supabase Postgres + RLS (Multi-Tenant)",
        "quadrant": "platforms", "ring": "ADOPT",
        "agent": "DB",
        "description": "Banco de dados relacional com isolamento de tenant em nível de linha (RLS)."
    },
    {
        "name": "MediaMTX (RTSP/WebRTC Streaming)",
        "quadrant": "platforms", "ring": "ADOPT",
        "agent": "Gateway",
        "description": "Servidor de mídia de baixíssima latência para streaming de câmeras IP."
    },
    {
        "name": "Railway / Docker Container Delivery",
        "quadrant": "platforms", "ring": "ADOPT",
        "agent": "Deploy",
        "description": "Deploy automatizado de contêineres otimizados para produção."
    },
    {
        "name": "Local CPU-First AI Inference (OpenVINO)",
        "quadrant": "platforms", "ring": "ADOPT",
        "agent": "AI_Edge",
        "description": "Inferência de alta performance na borda sem necessidade obrigatória de GPU discreta."
    },

    # ── TOOLS ──
    {
        "name": "code-review-graph MCP",
        "quadrant": "tools", "ring": "ADOPT",
        "agent": "Master",
        "description": "Grafo de conhecimento de código para análise de impacto e callers."
    },
    {
        "name": "Playwright Visual Regression Testing",
        "quadrant": "tools", "ring": "TRIAL",
        "agent": "UI",
        "description": "Testes E2E visuais com captura de screenshots e diffs pixel-a-pixel."
    },
    {
        "name": "Fast-Check / Property Testing Harness",
        "quadrant": "tools", "ring": "TRIAL",
        "agent": "Logs",
        "description": "Motor de testes de propriedades para contratos críticos de risco e fusão."
    },
    {
        "name": "Self-Improvement Audit Engine (audit_skills.py)",
        "quadrant": "tools", "ring": "ADOPT",
        "agent": "Master",
        "description": "Auditoria contínua da qualidade e completude dos SKILL.md (0-100 score)."
    },

    # ── FRAMEWORKS ──
    {
        "name": "Drizzle ORM (TypeScript)",
        "quadrant": "frameworks", "ring": "ADOPT",
        "agent": "DB",
        "description": "ORM fortemente tipado com geração determinística de migrations."
    },
    {
        "name": "FastAPI + Pydantic v2 (Python)",
        "quadrant": "frameworks", "ring": "ADOPT",
        "agent": "AI_Edge",
        "description": "Microserviço assíncrono de IA de alta performance e validação estrita."
    },
    {
        "name": "XState / Zustand (State Management)",
        "quadrant": "frameworks", "ring": "TRIAL",
        "agent": "UI",
        "description": "Máquinas de estado determinísticas para fluxos críticos de alarme e COPOM."
    },
    {
        "name": "Zod Validation Pipelines",
        "quadrant": "frameworks", "ring": "ADOPT",
        "agent": "Security",
        "description": "Validação de schemas em tempo de execução em todas as fronteiras de API."
    },
    {
        "name": "LangChain Heavy Frameworks",
        "quadrant": "frameworks", "ring": "HOLD",
        "agent": "Orchestrator",
        "description": "Anti-padrão: bibliotecas de agentes pesadas/opacas adicionam fragilidade e overhead."
    }
]


def display_radar(quadrant_filter: str = None):
    print(f"\n{SEPARATOR}")
    print("  🛰️  AntecipIA Tech Radar — Aerospace Standard v3.0")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(SEPARATOR)

    for q_key, q_title in RADAR_QUADRANTS.items():
        if quadrant_filter and quadrant_filter.lower() not in q_key:
            continue

        print(f"\n📂 [{q_key.upper()}] — {q_title}")
        print("─" * 70)

        items_in_q = [t for t in TECH_REGISTRY if t["quadrant"] == q_key]

        for r_key, r_desc in RADAR_RINGS.items():
            items_in_r = [t for t in items_in_q if t["ring"] == r_key]
            if not items_in_r:
                continue

            print(f"  {r_desc}:")
            for item in items_in_r:
                agent_tag = f"[@{item['agent']}]" if item.get("agent") else ""
                print(f"     • {item['name']:<38} {agent_tag:<12} — {item['description']}")

    print(f"\n{SEPARATOR}")
    total = len(TECH_REGISTRY)
    adopt = sum(1 for t in TECH_REGISTRY if t['ring'] == 'ADOPT')
    trial = sum(1 for t in TECH_REGISTRY if t['ring'] == 'TRIAL')
    assess = sum(1 for t in TECH_REGISTRY if t['ring'] == 'ASSESS')
    hold = sum(1 for t in TECH_REGISTRY if t['ring'] == 'HOLD')
    print(f"  📊 Estatísticas do Radar: {total} Tecnologias")
    print(f"     🟢 ADOPT: {adopt}  |  🟡 TRIAL: {trial}  |  🔵 ASSESS: {assess}  |  🔴 HOLD: {hold}")
    print(SEPARATOR + "\n")


def export_radar_json():
    RADAR_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": "3.0",
        "last_updated": datetime.now().isoformat(),
        "quadrants": RADAR_QUADRANTS,
        "rings": RADAR_RINGS,
        "technologies": TECH_REGISTRY
    }
    RADAR_DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Tech Radar exportado em: {RADAR_DATA_FILE}")


def main():
    parser = argparse.ArgumentParser(description="Radar Tecnológico do AntecipIA.")
    parser.add_argument("--quadrant", "-q", choices=list(RADAR_QUADRANTS.keys()),
                        help="Filtrar por quadrante específico")
    parser.add_argument("--export-json", "-e", action="store_true",
                        help="Exportar os dados para tech_radar.json")
    args = parser.parse_args()

    display_radar(args.quadrant)

    if args.export_json or not RADAR_DATA_FILE.exists():
        export_radar_json()


if __name__ == "__main__":
    main()
