#!/usr/bin/env python3
"""
propose_improvements.py — AntecipIA Agent Platform v2.0 — Self-Improvement Engine
Analisa os resultados de auditoria e gera um IMPROVEMENT_PROPOSAL.md para aprovação do CTO.
Uso: python .agents/self_improvement/scripts/propose_improvements.py
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

AGENTS_DIR = Path(__file__).parent.parent.parent
SKILLS_DIR = AGENTS_DIR / "skills"
MEMORY_DIR = AGENTS_DIR / "memory"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"
PROPOSAL_FILE = AGENTS_DIR / "self_improvement" / "IMPROVEMENT_PROPOSAL.md"

SEPARATOR = "═" * 65

QUALITY_CRITERIA = {
    "file_boundary":         {"pattern": r"File Boundary|Jurisdição Exclusiva|Fronteira de Domínio", "fix": "Adicionar seção '## 🛑 File Boundaries (Fronteira de Domínio)' com jurisdição explícita e proibições."},
    "handoff_rules":         {"pattern": r"Handoff|Regra.*Handoff|Delegação", "fix": "Adicionar seção '## ⚙️ Regra de Handoff' definindo quem recebe o próximo passo na esteira."},
    "self_review":           {"pattern": r"Auto-Reflexão|Self-Review|checklist", "fix": "Adicionar seção '## 🔄 Protocolo de Auto-Reflexão Pré-Handoff' com checklist de 3-5 itens."},
    "code_review_graph":     {"pattern": r"code-review-graph|Code Review Graph|query_graph_tool|detect_changes", "fix": "Adicionar seção '## 🧭 Ferramenta Obrigatória de Investigação (Code Review Graph)' com mandato e ferramentas específicas."},
    "inviolable_barriers":   {"pattern": r"Barreiras Invioláveis|PROIBIDO|ESTRITAMENTE PROIBIDO", "fix": "Adicionar seção '## 🛡️ Barreiras Invioláveis' com pelo menos 3 regras de PROIBIDO."},
    "technical_stack":       {"pattern": r"`[a-zA-Z_.-]+\.(ts|py|go|json|md)`|pnpm|npm|tsx|drizzle|supabase", "fix": "Adicionar referências técnicas concretas: comandos, arquivos e ferramentas específicas do domínio do agente."},
    "links_to_files":        {"pattern": r"file:///|`[a-z/.-]+/[a-z.-]+\.[a-z]+`", "fix": "Adicionar links file:/// para os arquivos mais importantes do domínio do agente."},
    "minimal_length":        {"pattern": None, "fix": "Expandir o SKILL.md para pelo menos 30 linhas com conteúdo substancial."}
}

def score_skill(content: str, lines: int) -> list:
    gaps = []
    for key, criterion in QUALITY_CRITERIA.items():
        if key == "minimal_length":
            if lines < 30:
                gaps.append({"key": key, "fix": criterion["fix"]})
        else:
            if not re.search(criterion["pattern"], content, re.IGNORECASE):
                gaps.append({"key": key, "fix": criterion["fix"]})
    return gaps

def main():
    print(f"\n{SEPARATOR}")
    print(f"  🔧 Self-Improvement Engine — Gerador de Propostas")
    print(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(SEPARATOR)

    if not SKILLS_DIR.exists():
        print(f"[ERRO] Diretório de skills não encontrado: {SKILLS_DIR}")
        sys.exit(1)

    skills = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])
    proposals = []

    for skill_dir in skills:
        skill_name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text(encoding="utf-8")
        lines = len(content.splitlines())
        gaps = score_skill(content, lines)

        if gaps:
            proposals.append({
                "agent": skill_name,
                "skill_path": str(skill_file),
                "current_lines": lines,
                "gaps": gaps
            })

    if not proposals:
        print("[OK] Nenhuma proposta de melhoria necessária. Todos os agentes estão acima do padrão mínimo.")
        sys.exit(0)

    # Gerar documento de proposta
    doc_lines = [
        f"# 🔧 Proposta de Melhorias dos Agentes — Auto-Gerada",
        f"",
        f"> **Gerado por:** Self-Improvement Engine  ",
        f"> **Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"> **Status:** AGUARDANDO APROVAÇÃO DO CTO  ",
        f"",
        f"---",
        f"",
        f"## Resumo",
        f"",
        f"Foram identificados **{len(proposals)} agentes** com gaps de qualidade nas suas skills.",
        f"Revise as propostas abaixo e aprove as melhorias desejadas.",
        f"",
        f"---",
        f""
    ]

    for i, proposal in enumerate(proposals, 1):
        agent = proposal["agent"]
        path = proposal["skill_path"]
        gaps = proposal["gaps"]

        doc_lines += [
            f"## {i}. [{agent}]({path.replace(chr(92), '/')})",
            f"",
            f"**Arquivo:** `{path}`  ",
            f"**Linhas atuais:** {proposal['current_lines']}  ",
            f"**Gaps encontrados:** {len(gaps)}",
            f"",
            f"### Melhorias Propostas:",
            f""
        ]
        for gap in gaps:
            doc_lines.append(f"- [ ] **{gap['key'].replace('_', ' ').title()}**: {gap['fix']}")
        doc_lines.append("")
        doc_lines.append("---")
        doc_lines.append("")

    doc_lines += [
        f"## Instruções para Aprovação",
        f"",
        f"1. Marque os checkboxes `[x]` para as melhorias que deseja aplicar.",
        f"2. Execute: `python .agents/self_improvement/scripts/apply_improvements.py`",
        f"3. O script aplicará apenas os itens marcados com `[x]`.",
        f""
    ]

    PROPOSAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROPOSAL_FILE.write_text("\n".join(doc_lines), encoding="utf-8")

    print(f"\n[OK] Proposta gerada em: {PROPOSAL_FILE}")
    print(f"[INFO] {len(proposals)} agente(s) com gaps identificados.")
    print(f"\n  Próximo passo: Revise {PROPOSAL_FILE} e aprove as melhorias.")
    print(SEPARATOR + "\n")

    # Log
    if SESSION_LOG.parent.exists():
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "SelfImprovement",
            "event": "proposals_generated",
            "agents_with_gaps": len(proposals)
        }
        with open(SESSION_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
