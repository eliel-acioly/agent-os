#!/usr/bin/env python3
"""
audit_skills.py — AntecipIA Agent Platform v2.0 — Self-Improvement Engine
Audita todos os SKILL.md dos agentes e gera um relatório de score por agente.
Detecta gaps críticos e propõe pontuação 0-100 para cada agente.
Uso: python .agents/self_improvement/scripts/audit_skills.py
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

AGENTS_DIR = Path(__file__).parent.parent.parent  # .agents/
SKILLS_DIR = AGENTS_DIR / "skills"
MEMORY_DIR = AGENTS_DIR / "memory"
METRICS_FILE = MEMORY_DIR / "agent_metrics.json"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"

SEPARATOR = "═" * 65

# Critérios obrigatórios em cada SKILL.md e seu peso
QUALITY_CRITERIA = {
    "file_boundary":         {"pattern": r"File Boundary|Jurisdição Exclusiva|Fronteira de Domínio", "weight": 15, "desc": "File Boundary definido"},
    "handoff_rules":         {"pattern": r"Handoff|Regra.*Handoff|Delegação", "weight": 15, "desc": "Regras de Handoff"},
    "self_review":           {"pattern": r"Auto-Reflexão|Self-Review|checklist", "weight": 15, "desc": "Protocolo de Auto-Reflexão"},
    "code_review_graph":     {"pattern": r"code-review-graph|Code Review Graph|query_graph_tool|detect_changes", "weight": 15, "desc": "code-review-graph MCP"},
    "inviolable_barriers":   {"pattern": r"Barreiras Invioláveis|PROIBIDO|ESTRITAMENTE PROIBIDO", "weight": 15, "desc": "Barreiras Invioláveis"},
    "technical_stack":       {"pattern": r"`[a-zA-Z_.-]+\.(ts|py|go|json|md)`|pnpm|npm|tsx|drizzle|supabase", "weight": 10, "desc": "Referências técnicas concretas"},
    "links_to_files":        {"pattern": r"file:///|`[a-z/.-]+/[a-z.-]+\.[a-z]+`", "weight": 10, "desc": "Links para arquivos reais"},
    "minimal_length":        {"pattern": None, "weight": 5, "desc": "Conteúdo suficiente (≥30 linhas)"}
}

def score_skill(skill_path: Path) -> dict:
    if not skill_path.exists():
        return {"score": 0, "gaps": ["SKILL.md não encontrado"], "content_lines": 0}

    content = skill_path.read_text(encoding="utf-8")
    lines = len(content.splitlines())
    gaps = []
    score = 0

    for key, criterion in QUALITY_CRITERIA.items():
        if key == "minimal_length":
            if lines >= 30:
                score += criterion["weight"]
            else:
                gaps.append(f"Conteúdo insuficiente ({lines} linhas — mínimo: 30)")
        else:
            pattern = criterion["pattern"]
            if re.search(pattern, content, re.IGNORECASE):
                score += criterion["weight"]
            else:
                gaps.append(criterion["desc"])

    return {"score": score, "gaps": gaps, "content_lines": lines}

def get_score_icon(score: int) -> str:
    if score >= 90: return "🟢"
    if score >= 70: return "🟡"
    if score >= 50: return "🟠"
    return "🔴"

def main():
    print(f"\n{SEPARATOR}")
    print(f"  🧠 Self-Improvement Engine — Auditoria de Agentes v2.0")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(SEPARATOR)

    if not SKILLS_DIR.exists():
        print(f"[ERRO] Diretório de skills não encontrado: {SKILLS_DIR}")
        sys.exit(1)

    all_results = {}
    skills = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])

    print(f"\n{'Agente':<30} {'Score':>8}  {'Status':<12} {'Gaps'}")
    print("─" * 65)

    for skill_dir in skills:
        skill_name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        result = score_skill(skill_file)
        all_results[skill_name] = result
        score = result["score"]
        icon = get_score_icon(score)
        gaps_count = len(result["gaps"])
        gap_summary = f"{gaps_count} gap(s)" if gaps_count > 0 else "Nenhum gap!"
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        print(f"  {icon} {skill_name:<27} {score:>3}/100  [{bar}]  {gap_summary}")

    # Relatório detalhado de gaps
    print(f"\n{'─' * 65}")
    print("  📋 GAPS DETALHADOS POR AGENTE")
    print("─" * 65)
    has_gaps = False
    for skill_name, result in all_results.items():
        if result["gaps"]:
            has_gaps = True
            print(f"\n  ❌ {skill_name}:")
            for gap in result["gaps"]:
                print(f"     • {gap}")

    if not has_gaps:
        print("  ✅ Nenhum gap crítico encontrado em todos os agentes!")

    # Score médio
    avg_score = sum(r["score"] for r in all_results.values()) // len(all_results) if all_results else 0
    total_gaps = sum(len(r["gaps"]) for r in all_results.values())

    print(f"\n{SEPARATOR}")
    print(f"  📊 SCORE MÉDIO DA PLATAFORMA: {avg_score}/100  {get_score_icon(avg_score)}")
    print(f"  ⚠️  Total de gaps a corrigir: {total_gaps}")
    print(SEPARATOR)

    # Atualizar métricas
    if METRICS_FILE.exists():
        metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))
        for skill_name, result in all_results.items():
            agent_key = skill_name.replace("antecipia-", "").replace("-", "_").title()
            if agent_key in metrics.get("agents", {}):
                metrics["agents"][agent_key]["skill_score"] = result["score"]
        METRICS_FILE.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[OK] Scores atualizados em agent_metrics.json")

    # Log de sessão
    if SESSION_LOG.parent.exists():
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "SelfImprovement",
            "event": "audit_completed",
            "avg_score": avg_score,
            "total_gaps": total_gaps
        }
        with open(SESSION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    if avg_score < 70:
        print("\n[RECOMENDAÇÃO] Execute propose_improvements.py para gerar sugestões de melhoria.")
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
