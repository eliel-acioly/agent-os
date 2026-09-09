#!/usr/bin/env python3
"""
context_engine.py — Agent-OS 2.0 Agentic Context Engineering (por projeto).

O agente não recebe "20 chunks". Recebe um bloco montado e verificado:

  FACTS / CONSTRAINTS / RELEVANT ENTITIES / DEPENDENCIES /
  PREVIOUS EXPERIENCES / RISKS / AVAILABLE TOOLS / VERIFICATION PLAN

Montagem: retrieve (router) -> compress (top-k por origem) -> prioritize
(símbolos e dependências diretas primeiro) -> deduplicate -> verify
(grounding: toda entidade precisa existir no code graph ou filesystem) -> assemble.

Uso:
  python .agents/scripts/context_engine.py --mission "Corrigir filtro subcategory" --agent API
  python .agents/scripts/context_engine.py --mission "..." --agent UI --json
"""
import sys
import os
import re
import json
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "rag"))
from project_context import get_project_root, get_agents_dir, get_project_slug

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)

SEP = "=" * 70

AGENT_TOOLS = {
    "API": ["read_file", "edit_backend(app/api/,lib/)", "run_tsc", "run_tests", "query_rag", "blast_radius"],
    "UI": ["read_file", "edit_frontend(app/,components/)", "run_tsc", "query_rag", "blast_radius"],
    "DB": ["read_schema(src/db/,supabase/)", "drizzle_generate", "query_rag"],
    "Logs": ["run_tests", "run_tsc", "read_logs", "query_rag"],
    "Security": ["secrets_scan", "read_routes", "query_rag"],
    "Master": ["validate_pipeline", "run_tsc", "merge_gate", "query_rag"],
    "Contracts": ["read_contracts(shared/contracts/)", "query_rag"],
    "Gateway": ["read_services", "go_build", "query_rag"],
    "AI_Edge": ["read_workers", "query_rag"],
    "Deploy": ["migrations_apply", "deploy_check", "query_rag"],
    "Orchestrator": ["plan", "delegate", "query_rag"],
}


def _exists_in_project(path: str) -> bool:
    return (PROJECT_ROOT / path).is_file()


def assemble(mission: str, agent: str = "Master", top_k: int = 5) -> dict:
    from query_engine import route_query, query_rag, symbol_candidates
    plan = route_query(mission)
    results = query_rag(mission, agent, top_k * 2)

    # ENTITIES (verificadas: símbolo no graph ou arquivo no filesystem)
    entities, seen = [], set()
    for cand in symbol_candidates(mission, top_k=6):
        key = (cand["source"], cand["start_line"])
        if key in seen:
            continue
        seen.add(key)
        if _exists_in_project(cand["source"]):
            entities.append({"name": cand["text"].split("—")[0].strip(),
                             "file": cand["source"], "line": cand["start_line"],
                             "grounded": True})

    # DEPENDENCIES (callers dos arquivos-entidade)
    dependencies = []
    try:
        from code_graph import callers_of
        for e in entities[:3]:
            for r in callers_of(e["file"], limit=5):
                if r["file"] not in {d["file"] for d in dependencies}:
                    dependencies.append({"file": r["file"], "via": r["via"]})
    except Exception:
        pass

    # FACTS: top resultados com proveniência, deduplicados
    facts = []
    for r in results[:top_k]:
        facts.append({"source": r.get("source"), "lines": [r.get("start_line"), r.get("end_line")],
                      "relevance": r.get("relevance"), "via": r.get("retrieval_source", []),
                      "excerpt": (r.get("text") or "")[:220]})

    # EXPERIENCES
    experiences = []
    try:
        sys.path.insert(0, str(AGENTS_DIR / "scripts"))
        from memory_consolidate import retrieve
        for h in retrieve(mission, agent, 2):
            experiences.append({"lesson": h.get("lesson", "")[:220], "utility": h.get("utility")})
    except Exception:
        pass

    # RISKS (heurística honesta por superfície tocada)
    files = {e["file"] for e in entities} | {d["file"] for d in dependencies} | \
            {f["source"] for f in facts if isinstance(f.get("source"), str) and not f["source"].startswith(("memory:", "git:"))}
    risks = []
    if any(f.startswith("app/api/") for f in files):
        risks.append("API incompatível: validar contratos em shared/contracts/ e consumidores.")
    if any("schema" in f or "supabase" in f or "migration" in f for f in files):
        risks.append("Banco inconsistente: migration + RLS precisam acompanhar o código.")
    if any(f.startswith(("app/", "components/")) for f in files):
        risks.append("UI quebrada: checar os 5 estados (Loading/Empty/Error/Offline/Success).")
    if len(files) > 8:
        risks.append(f"Blast amplo ({len(files)} arquivos): mudança mínima + verificação por etapa.")
    if not entities and not facts:
        risks.append("Contexto fraco (sem entidades ancoradas): recuperar mais antes de codificar.")

    # CONSTRAINTS por agente (domínios)
    constraints = {
        "UI": ["Não editar app/api/*, src/db/*, supabase/*"],
        "API": ["Não editar src/db/*, supabase/*, components/*"],
        "DB": ["Apenas src/db/*, supabase/*, migrations; exportar tipos"],
        "Logs": ["Não editar código de produção; devolver com logs"],
    }.get(agent, ["Respeitar jurisdição do agente e HANDOFF.md"])

    # VERIFICATION PLAN (risco -> verificações)
    verification = ["pnpm tsc --noEmit"]
    if any(f.startswith("app/api/") for f in files):
        verification.append("testes das rotas afetadas + contrato")
    if any("test" in (f.get("source") or "") for f in facts):
        verification.append("rodar testes relacionados listados acima")
    verification.append("agent_guardrails --all antes do handoff")

    return {
        "project": PROJECT_SLUG, "agent": agent, "mission": mission,
        "intent": plan["intent"], "mechanisms": plan["mechanisms"],
        "facts": facts, "constraints": constraints,
        "entities": entities, "dependencies": dependencies[:10],
        "experiences": experiences, "risks": risks,
        "tools": AGENT_TOOLS.get(agent, AGENT_TOOLS["Master"]),
        "verification_plan": verification,
        "confidence": {
            "retrieval": round(min(0.95, 0.4 + 0.1 * len(facts)), 2),
            "graph": 0.9 if entities else 0.3,
            "memory": round(min(0.9, 0.4 + 0.2 * len(experiences)), 2),
        },
    }


def render(ctx: dict) -> str:
    L = [f"CONTEXT [{ctx['project']}] intent={ctx['intent']}"]
    L.append("FACTS:")
    for f in ctx["facts"][:5]:
        L.append(f"  - {f['source']}:{f['lines'][0]} (rel {f['relevance']}, via {','.join(f['via'])})")
    L.append("CONSTRAINTS:")
    for c in ctx["constraints"]:
        L.append(f"  - {c}")
    L.append("ENTITIES:")
    for e in ctx["entities"][:6]:
        L.append(f"  - {e['name']} @ {e['file']}:{e['line']}")
    L.append("DEPENDENCIES:")
    for d in ctx["dependencies"][:8]:
        L.append(f"  - {d['file']} ({d['via']})")
    L.append("EXPERIENCES:")
    for e in ctx["experiences"][:3]:
        L.append(f"  - [u={e['utility']}] {e['lesson'][:160]}")
    L.append("RISKS:")
    for r in ctx["risks"]:
        L.append(f"  - {r}")
    L.append("TOOLS: " + ", ".join(ctx["tools"]))
    L.append("VERIFICATION PLAN:")
    for v in ctx["verification_plan"]:
        L.append(f"  [ ] {v}")
    L.append(f"CONFIDENCE: {ctx['confidence']}")
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description="Monta contexto verificado por projeto.")
    p.add_argument("--mission", "-m", required=True)
    p.add_argument("--agent", "-a", default="Master")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    ctx = assemble(args.mission, args.agent.replace("@", ""))
    if args.json:
        print(json.dumps(ctx, indent=2, ensure_ascii=False))
    else:
        print(f"{SEP}\n  {render(ctx)}\n{SEP}")


if __name__ == "__main__":
    main()
