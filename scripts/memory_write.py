#!/usr/bin/env python3
"""
memory_write.py — AntecipIA Agent Platform v2.0
Persiste um aprendizado ou padrão novo na base de conhecimento do agente.
Uso: python .agents/scripts/memory_write.py --agent API --type learning --text "Sempre validar DTOs com Zod"
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

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

    # Log de sessão
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "event": "memory_written",
        "type": entry_type,
        "text": text
    }
    with open(SESSION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(f"[OK] Memória persistida para @{agent_name}:")
    print(f"     Tipo: {entry_type}")
    print(f"     Texto: {text}")

if __name__ == "__main__":
    main()
