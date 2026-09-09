#!/usr/bin/env python3
"""
memory_write.py — Agent-OS (agnóstico a projeto)
Persiste um aprendizado ou padrão novo na base de conhecimento do agente.
Uso: python .agents/scripts/memory_write.py --agent API --type learning --text "Sempre validar DTOs com Zod"
"""

import sys
import json
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

# Instrumentação de observabilidade (spans com duração/modelo/tokens)
import metrics_hook as _mh

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))
try:
    from project_context import get_project_root, get_agents_dir, get_project_slug
    PROJECT_ROOT = get_project_root()
    PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
except Exception:
    PROJECT_SLUG = "proj"

AGENTS_DIR = Path(__file__).parent.parent
MEMORY_DIR = AGENTS_DIR / "memory"
KNOWLEDGE_BASE = MEMORY_DIR / "knowledge_base.json"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"

def load_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}

def save_json(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Persiste aprendizado na memória do agente.")
    parser.add_argument("--agent", "-a", required=True, help="Nome do agente (ex: API, UI, Logs)")
    parser.add_argument("--type", "-t", choices=["learning", "pattern", "blocker"], default="learning",
                        help="Tipo do registro: learning (lição), pattern (padrão), blocker (bloqueio)")
    parser.add_argument("--text", "-x", required=True, help="Texto do aprendizado ou padrão")
    args = parser.parse_args()

    _start_ts = time.time()
    agent_name = args.agent.strip().replace("@", "")
    entry_type = args.type
    text = args.text.strip()

    kb = load_json(KNOWLEDGE_BASE)
    agents_data = kb.setdefault("agents", {})
    agent_data = agents_data.setdefault(agent_name, {"learnings": [], "patterns": [], "blockers_history": []})

    key_map = {
        "learning": "learnings",
        "pattern": "patterns",
        "blocker": "blockers_history"
    }
    target_list = agent_data.setdefault(key_map[entry_type], [])

    if text in target_list:
        print(f"[AVISO] Entrada já existente na memória de @{agent_name}. Nenhuma duplicação realizada.")
        sys.exit(0)

    target_list.append(text)
    kb["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    save_json(KNOWLEDGE_BASE, kb)

    # Span de observabilidade (padrão tracing) — duração, modelo, tokens estimados, decisão
    _mh.record_span(
        agent_name,
        event="memory_written",
        duration_ms=(time.time() - _start_ts) * 1000,
        tokens=len(text) // 4,
        decision=entry_type,
        extra={"type": entry_type, "text": text[:200]},
    )

    print(f"[OK] Memória persistida para @{agent_name}:")
    print(f"     Tipo: {entry_type}")
    print(f"     Texto: {text}")

if __name__ == "__main__":
    main()
