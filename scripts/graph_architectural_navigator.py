#!/usr/bin/env python3
"""
AGENT-OS — GRAPH ARCHITECTURAL NAVIGATOR & GROUNDING ENGINE (agnóstico a projeto)
Capacidades:
1. Inspeção de componentes do PROJETO LINKADO (catálogo por projeto se existir).
2. Análise de Raio de Impacto Multi-Salto (via blast_radius real + AST se disponível).
3. Verificação de ancoragem (catalog por projeto + AST + filesystem — anti-alucinação).
4. Comunidades hierárquicas (por projeto se existir, senão genéricas).
"""

import sys
import os
import sqlite3
import argparse
import json
import re
from pathlib import Path

# Garante saída UTF-8 no terminal Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))
try:
    from project_context import get_project_root, get_agents_dir, get_project_slug
    PROJECT_ROOT = str(get_project_root())
    PROJECT_SLUG = get_project_slug(Path(PROJECT_ROOT))
except Exception:
    REPO_ROOT_FALLBACK = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    PROJECT_ROOT = os.getcwd() if os.path.isdir(os.path.join(os.getcwd(), ".agents")) else REPO_ROOT_FALLBACK
    PROJECT_SLUG = os.path.basename(PROJECT_ROOT) or "proj"

REPO_ROOT = PROJECT_ROOT
GRAPH_DB_PATH = os.path.join(REPO_ROOT, ".code-review-graph", "graph.db")
# Catálogo por projeto (opt-in): docs/architecture/catalog.json ou .agents/memory/projects/<slug>/catalog.json
PROJECT_CATALOG_PATHS = [
    os.path.join(REPO_ROOT, "docs", "architecture", "catalog.json"),
    os.path.join(REPO_ROOT, ".agents", "memory", "projects", PROJECT_SLUG, "catalog.json"),
]

# Base de Conhecimento Arquitetural LEGADA (exemplo AntecipIA — mantida como fallback).
# Para o projeto linkado, crie docs/architecture/catalog.json com o mesmo formato
# {"Componente": {"community": "...", "description": "...", ...}} para substituir.
ARCHITECTURAL_CATALOG = {
    "TenantsController": {
        "community": "C1_RETAIL_SALON",
        "description": "Controller de gestão de workspaces, zonificações, heatmaps térmicos, filas e oportunidades do lojista.",
        "ontology_entity": "Context, Event, Recommendation, Outcome",
        "authorizing_spec": "SPEC-DOM-RETAIL-001 (Salão de Vendas) & SPEC-INT-001 (Contexto Externo)",
        "contracts": ["shared/contracts/types/retail-analytics.ts", "shared/contracts/types/opportunities.ts"],
        "adrs": ["ADR-003 (Domain Routing)", "ADR-005 (Reality-First Data)"],
        "tests": ["docs/testes/2026-08/test_fase_c_boutique_pilot_e2e.ts", "docs/testes/2026-08/test_gate2_seed_reproducibility_e2e.ts"]
    },
    "DemoController": {
        "community": "C0_CORE_PLATFORM",
        "description": "Controller de demonstração assistida e reset determinístico idempotente em <1000ms.",
        "ontology_entity": "Context, Outcome",
        "authorizing_spec": "SPEC-CORE-002 (Demo Engine & Reset Determinístico)",
        "contracts": ["shared/contracts/types/onboarding.ts (ResetDemoStateDTO, DemoScenarioDTO)"],
        "adrs": ["ADR-005 (Reality-First Data)"],
        "tests": ["docs/testes/2026-08/test_fase_d_pilot_ready_e2e.ts"]
    },
    "ConnectController": {
        "community": "C2_EDGE_INGESTION",
        "description": "Controller do AntecipIA Connect para descoberta autônoma ONVIF/LAN e ponte de vídeo sem abertura de portas.",
        "ontology_entity": "Observation, Context",
        "authorizing_spec": "SPEC-INT-002 (AntecipIA Connect Edge Bridge)",
        "contracts": ["shared/contracts/types/connect.ts (ConnectAgentDTO, DiscoveredDeviceDTO)"],
        "adrs": ["ADR-003 (Domain Routing)"],
        "tests": ["docs/testes/2026-08/test_fase_d_pilot_ready_e2e.ts", "docs/testes/2026-08/test_antecipia_connect_flow.ts"]
    },
    "AlertsController": {
        "community": "C1_URBAN_COPOM",
        "description": "Ingestão de pânico, despacho móvel via WhatsApp e emissão de laudos forenses periciais.",
        "ontology_entity": "Event, Action, Outcome",
        "authorizing_spec": "SPEC-DOM-URBAN-001 & SPEC-INT-003 (Despacho Operacional Móvel)",
        "contracts": ["shared/contracts/types/incidents.ts", "shared/contracts/types/alert-channels.ts"],
        "adrs": ["ADR-001 (REST XAI com CognitionQueue)", "ADR-003 (Domain Routing)"],
        "tests": ["docs/testes/2026-08/test_fase_d_pilot_ready_e2e.ts", "docs/testes/2026-08/test_forensic_reports_pdf_e2e.ts"]
    },
    "RiskBuilder": {
        "community": "C0_CORE_PLATFORM",
        "description": "Motor de Fusão Bayesiana e Dempster-Shafer que calcula índices de risco situacional a partir de evidências de atores.",
        "ontology_entity": "Inference, Risk, Hypothesis",
        "authorizing_spec": "SPEC-INF-001 (Motores de Inferência Bayesiana e XAI)",
        "contracts": ["shared/contracts/types/ontology.ts (RiskIndices, Hypothesis, Evidence)"],
        "adrs": ["ADR-001 (REST XAI)", "ADR-003 (Domain Routing)"],
        "tests": ["docs/testes/2026-08/test_real_intelligence_core_mvp.ts"]
    },
    "authMiddleware": {
        "community": "C0_CORE_PLATFORM",
        "description": "Middleware híbrido de autenticação e RBAC validando tokens JWKS ES256 (Supabase) e HS256.",
        "ontology_entity": "Context, Profile, Workspace",
        "authorizing_spec": "SPEC-IDENT-001 (Multi-tenancy e RBAC)",
        "contracts": ["shared/contracts/types/workspaces.ts", "shared/contracts/types/permissions.ts"],
        "adrs": ["ADR-004 (Supabase Auth Hybrid JWKS)"],
        "tests": ["docs/testes/2026-08/test_hardening_auth_plan_rbac_e2e.ts", "docs/testes/2026-08/test_gate4_owner_manager_isolation_e2e.ts"]
    },
    "requirePlanModule": {
        "community": "C0_CORE_PLATFORM",
        "description": "Middleware de Plan Guard que intercepta requisições e bloqueia módulos não contratados.",
        "ontology_entity": "Risk, Context",
        "authorizing_spec": "SPEC-SEC-001 (Plan Guard & Governança de Monetização)",
        "contracts": ["shared/contracts/types/monetization.ts (ProductTier, WorkspaceModuleKey)"],
        "adrs": ["ADR-003 (Domain Routing & Contracts)"],
        "tests": ["docs/testes/2026-08/test_gate5_plan_tier_guard_e2e.ts"]
    },
    "RetailDashboard": {
        "community": "C1_RETAIL_SALON",
        "description": "Superfície de experiência do usuário para o lojista B2B (Resumo Matinal, Heatmap, Radar de Filas, Ledger).",
        "ontology_entity": "Context, Observation, Event, Outcome",
        "authorizing_spec": "SPEC-DOM-RETAIL-001 & SPEC-UI-001",
        "contracts": ["shared/contracts/types/retail-analytics.ts", "shared/contracts/types/opportunities.ts"],
        "adrs": ["ADR-005 (Reality-First Data Policy)"],
        "tests": ["antecipia-ui/scripts/record_retail_flow.cjs"]
    },
    "CopomDashboard": {
        "community": "C1_URBAN_COPOM",
        "description": "Superfície de comando e controle operacional para segurança pública urbana (Live Map, Despacho 190, Pânico).",
        "ontology_entity": "Event, Action",
        "authorizing_spec": "SPEC-DOM-URBAN-001 (Segurança Pública e COPOM)",
        "contracts": ["shared/contracts/types/incidents.ts", "shared/contracts/types/alert-channels.ts"],
        "adrs": ["ADR-003 (Domain Routing & Dictionaries)"],
        "tests": ["docs/testes/2026-08/test_fase_d_pilot_ready_e2e.ts"]
    }
}

# Macro-Comunidades Hierárquicas LEGADAS (fallback). Por projeto: docs/architecture/communities.json
COMMUNITY_DEFINITIONS = {
    "C0_CORE_PLATFORM": {
        "title": "Núcleo Cognitivo Universal",
        "description": "Motor agnóstico de fusão de evidências, cálculo bayesiano de risco, ledger de valor e orquestração de banco.",
        "components": ["RiskBuilder", "DemoController", "authMiddleware", "requirePlanModule", "seed.ts", "schema.ts"]
    },
    "C1_RETAIL_SALON": {
        "title": "Módulo Varejo: Salão de Vendas & Operação B2B",
        "description": "Adaptação vertical para lojas físicas: heatmap contínuo, radar de filas, dwell time e correlação com conversão PDV.",
        "components": ["TenantsController", "RetailDashboard", "atendimentoFilas", "zonasLoja", "oportunidadesLojista"]
    },
    "C1_URBAN_COPOM": {
        "title": "Módulo Urbano: Segurança Pública & COPOM B2G",
        "description": "Adaptação vertical de monitoramento avançado: Live Map georreferenciado, botões de pânico, despacho 190 e laudo pericial.",
        "components": ["AlertsController", "CopomDashboard", "alertasPanico", "ForensicReportService", "WhatsAppService"]
    },
    "C2_EDGE_INGESTION": {
        "title": "Borda, Streaming & Conectividade LAN",
        "description": "Ponte de vídeo local, descoberta ONVIF/RTSP, MediaMTX e telemetria de sensores.",
        "components": ["ConnectController", "connectAgents", "MediaMtxAuthController", "antecipia-gateway"]
    },
    "C3_SHARED_CONTRACTS": {
        "title": "Camada de Contratos Única (SSOT)",
        "description": "Tipos TypeScript congelados e contratos compartilhados entre Frontend e Backend.",
        "components": ["ontology.ts", "onboarding.ts", "alert-channels.ts", "connect.ts", "retail-analytics.ts"]
    }
}

def _load_project_catalog() -> dict:
    for p in PROJECT_CATALOG_PATHS:
        try:
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data:
                        return data
        except Exception:
            continue
    return {}


def _effective_catalog() -> dict:
    proj = _load_project_catalog()
    if proj:
        return proj
    return ARCHITECTURAL_CATALOG


def _term_exists_in_project(term: str) -> str | None:
    """Verifica se o termo existe como arquivo/símbolo no projeto linkado (fallback filesystem)."""
    t = (term or "").strip()
    if not t:
        return None
    # Caminho direto?
    for cand in (t, t + ".ts", t + ".tsx", t + ".py"):
        if os.path.isfile(os.path.join(REPO_ROOT, cand.replace("/", os.sep))):
            return cand
    # Busca por nome de arquivo (limitada, rápida)
    base = t.split("/")[-1].lower()
    if len(base) < 3:
        return None
    try:
        for root, dirs, files in os.walk(REPO_ROOT, topdown=True):
            dirs[:] = [d for d in dirs if d not in ("node_modules", ".next", ".git", "dist", "__pycache__", ".agents")]
            for fn in files:
                if base in fn.lower():
                    rel = os.path.relpath(os.path.join(root, fn), REPO_ROOT).replace(os.sep, "/")
                    return rel
            # Limita profundidade para não varrer tudo
            if root.count(os.sep) - REPO_ROOT.count(os.sep) > 5:
                dirs[:] = []
    except Exception:
        return None
    return None

def query_ast_graph(target_symbol):
    """Consulta chamadores, dependências e imports na base SQLite graph.db"""
    if not os.path.exists(GRAPH_DB_PATH):
        return {"nodes": [], "callers": [], "callees": []}
    
    conn = sqlite3.connect(GRAPH_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT source_qualified, kind, file_path, line 
        FROM edges 
        WHERE target_qualified LIKE ? AND kind IN ('CALLS', 'REFERENCES')
        LIMIT 10
    """, (f"%{target_symbol}%",))
    callers = [{"caller": row[0], "kind": row[1], "file": row[2], "line": row[3]} for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT target_qualified, kind, file_path, line 
        FROM edges 
        WHERE source_qualified LIKE ? AND kind IN ('CALLS', 'REFERENCES')
        LIMIT 10
    """, (f"%{target_symbol}%",))
    callees = [{"target": row[0], "kind": row[1], "file": row[2], "line": row[3]} for row in cursor.fetchall()]
    
    cursor.execute("""
        SELECT qualified_name, kind, file_path 
        FROM nodes 
        WHERE qualified_name LIKE ? 
        LIMIT 5
    """, (f"%{target_symbol}%",))
    nodes = [{"node": row[0], "kind": row[1], "file": row[2]} for row in cursor.fetchall()]
    
    conn.close()
    return {"nodes": nodes, "callers": callers, "callees": callees}

def compute_multi_hop_blast_radius(symbol):
    """Calcula o raio de impacto em 5 saltos (catálogo do projeto + AST + defaults genéricos)"""
    ast = query_ast_graph(symbol)
    catalog = None
    for k, v in _effective_catalog().items():
        if k.lower() in symbol.lower():
            catalog = v
            break

    hops = {
        "hop_1_ast_callers": [c["caller"] for c in ast["callers"]],
        "hop_2_contracts": catalog.get("contracts", ["shared/contracts/"]) if catalog else ["shared/contracts/"],
        "hop_3_spec": catalog.get("authorizing_spec", "Especificação do módulo") if catalog else "Especificação do módulo",
        "hop_4_protected_tests": catalog.get("tests", ["docs/testes/"]) if catalog else ["docs/testes/"],
        "hop_5_community": catalog.get("community", "C0_CORE") if catalog else "C0_CORE"
    }
    return hops

def verify_graph_grounding(terms_list):
    """Verifica termos contra catálogo do projeto, AST e filesystem (anti-alucinação)"""
    results = []
    conn = None
    if os.path.exists(GRAPH_DB_PATH):
        try:
            conn = sqlite3.connect(GRAPH_DB_PATH)
        except Exception:
            conn = None
    catalog = _effective_catalog()

    for term in terms_list:
        term_clean = term.strip()
        if not term_clean:
            continue

        # 1. Catálogo do projeto (ou legado como fallback)
        in_catalog = any(term_clean.lower() in k.lower() for k in catalog.keys())

        # 2. SQLite AST
        in_ast = False
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT 1 FROM nodes WHERE qualified_name LIKE ? LIMIT 1", (f"%{term_clean}%",))
                in_ast = c.fetchone() is not None
            except Exception:
                in_ast = False

        # 3. Filesystem do projeto linkado (evita falso UNVERIFIED para componentes reais)
        fs_hit = _term_exists_in_project(term_clean)
        in_fs = fs_hit is not None

        grounded = in_catalog or in_ast or in_fs
        if in_catalog:
            source = "CATALOG"
        elif in_ast:
            source = "AST_GRAPH"
        elif in_fs:
            source = f"FILESYSTEM:{fs_hit}"
        else:
            source = "NONE"
        results.append({
            "term": term_clean,
            "grounded": grounded,
            "status": "GROUNDED" if grounded else "UNVERIFIED_HALLUCINATION_RISK",
            "source": source
        })

    if conn:
        try:
            conn.close()
        except Exception:
            pass
    return results

def list_communities():
    """Retorna comunidades do projeto (ou fallback genérico)."""
    proj_path = os.path.join(REPO_ROOT, "docs", "architecture", "communities.json")
    try:
        if os.path.isfile(proj_path):
            with open(proj_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    return data
    except Exception:
        pass
    return COMMUNITY_DEFINITIONS

def main():
    parser = argparse.ArgumentParser(description="Agent-OS Graph Architectural Navigator & Grounding Engine (por projeto)")
    parser.add_argument("--component", "-c", help="Nome do componente, classe ou função a investigar")
    parser.add_argument("--blast-radius", action="store_true", help="Calcula o raio de impacto multi-salto do componente")
    parser.add_argument("--grounding-check", nargs="+", help="Verifica lista de termos contra o grafo para barrar alucinações")
    parser.add_argument("--communities", action="store_true", help="Lista as macro-comunidades hierárquicas particionadas")
    parser.add_argument("--json", action="store_true", help="Saída em formato JSON estruturado")
    args = parser.parse_args()

    # 1. Modo Verificação de Ancoragem (Grounding Anti-Alucinação)
    if args.grounding_check:
        grounding_report = verify_graph_grounding(args.grounding_check)
        if args.json:
            print(json.dumps(grounding_report, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print("  GRAPH GROUNDING VERIFIER (AERONAUTICAL INTEGRITY)")
            print("=" * 70)
            for item in grounding_report:
                icon = "🟢" if item["grounded"] else "🔴"
                print(f"  {icon} [{item['status']}] {item['term']} (Origem: {item['source']})")
            print("=" * 70)
        return

    # 2. Modo Listagem de Comunidades
    if args.communities:
        comms = list_communities()
        if args.json:
            print(json.dumps(comms, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print("  ANTECIPIA HIERARCHICAL COMMUNITIES (PARTICIONAMENTO LEIDEN)")
            print("=" * 70)
            for cid, data in comms.items():
                print(f"\n🏷️ [{cid}] {data['title']}")
                print(f"   Descrição: {data['description']}")
                print(f"   Componentes-Chave: {', '.join(data['components'])}")
            print("=" * 70)
        return

    # 3. Modo Componente e Blast Radius
    if args.component:
        symbol = args.component
        catalog_info = None
        for k, v in _effective_catalog().items():
            if k.lower() in symbol.lower():
                catalog_info = v
                break

        ast_info = query_ast_graph(symbol)
        blast_radius = compute_multi_hop_blast_radius(symbol) if args.blast_radius else None

        report = {
            "project": PROJECT_SLUG,
            "component": symbol,
            "is_cataloged": catalog_info is not None,
            "community": (catalog_info.get("community", "C0_CORE") if catalog_info else "C0_CORE"),
            "description": (catalog_info.get("description", "Componente do projeto.") if catalog_info else "Componente do projeto."),
            "ontology_entity": (catalog_info.get("ontology_entity", "Mapeado via filesystem/AST") if catalog_info else "Mapeado via filesystem/AST"),
            "authorizing_spec": (catalog_info.get("authorizing_spec", "Consulte docs/specs correspondente") if catalog_info else "Consulte docs/specs correspondente"),
            "contracts": (catalog_info.get("contracts", []) if catalog_info else []),
            "adrs": (catalog_info.get("adrs", []) if catalog_info else []),
            "tests": (catalog_info.get("tests", []) if catalog_info else []),
            "ast_nodes": ast_info.get("nodes", []),
            "callers": ast_info.get("callers", []),
            "callees": ast_info.get("callees", []),
            "blast_radius": blast_radius
        }

        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("=" * 70)
            print(f"  GRAPH ARCHITECTURAL NAVIGATOR [{PROJECT_SLUG}]: {symbol}")
            print("=" * 70)
            print(f"[Comunidade]: {report['community']}")
            print(f"[Propósito]: {report['description']}")
            print(f"[Entidade Ontológica]: {report['ontology_entity']}")
            print(f"[Spec Autorizadora]: {report['authorizing_spec']}")
            print(f"[Contratos / DTOs]: {', '.join(report['contracts']) if report['contracts'] else 'N/A'}")
            print(f"[ADRs Associadas]: {', '.join(report['adrs']) if report['adrs'] else 'N/A'}")
            print(f"[Testes que Protegem]: {', '.join(report['tests']) if report['tests'] else 'N/A'}")
            
            if blast_radius:
                print("-" * 70)
                print("💥 RAIO DE IMPACTO MULTI-SALTO (MULTI-HOP BLAST RADIUS):")
                print(f"  • Salto 1 (Chamadores AST): {', '.join(blast_radius['hop_1_ast_callers']) if blast_radius['hop_1_ast_callers'] else 'Invocação direta de rota'}")
                print(f"  • Salto 2 (Contratos Afetados): {', '.join(blast_radius['hop_2_contracts'])}")
                print(f"  • Salto 3 (Spec Guardiã): {blast_radius['hop_3_spec']}")
                print(f"  • Salto 4 (Suíte E2E Obrigatória): {', '.join(blast_radius['hop_4_protected_tests'])}")
                print(f"  • Salto 5 (Comunidade Envolvente): {blast_radius['hop_5_community']}")

            print("-" * 70)
            print(f"Grafo de Chamadas AST (Quem chama / Quem é chamado):")
            print(f"  • Chamadores ({len(report['callers'])} encontrados):")
            for c in report['callers'][:5]:
                print(f"    - [{c['kind']}] {c['caller']} ({c['file']}:{c['line']})")
            print(f"  • Chamados ({len(report['callees'])} encontrados):")
            for c in report['callees'][:5]:
                print(f"    - [{c['kind']}] {c['target']} ({c['file']}:{c['line']})")
            print("=" * 70)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
