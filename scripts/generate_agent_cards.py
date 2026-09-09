#!/usr/bin/env python3
"""
generate_agent_cards.py — A2A Agent Cards Generator (padrão Agent2Agent Protocol v1.0 / Linux Foundation)
Lê o frontmatter YAML (name/description) de cada SKILL.md em .agents/skills/ e gera
Agent Cards A2A + índice de descoberta em docs/agent-cards/.

Uso:
  python .agents/scripts/generate_agent_cards.py              # gera cards + índice
  python .agents/scripts/generate_agent_cards.py --validate    # valida cards existentes
  python .agents/scripts/generate_agent_cards.py --out docs/agent-cards
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
try:
    from project_context import get_project_root, get_agents_dir, get_project_slug
    PROJECT_ROOT = get_project_root()
    AGENTS_DIR = get_agents_dir()
    PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
except Exception:
    AGENTS_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = AGENTS_DIR.parent
    PROJECT_SLUG = "proj"

ROOT = PROJECT_ROOT
SKILLS_ROOT = AGENTS_DIR / "skills"
BASE_URL = "https://ligacommerce.com.br/agents"
PROVIDER = {"organization": "Agent-OS", "url": "https://ligacommerce.com.br"}
SEP = "=" * 70


def parse_frontmatter(md_text: str) -> dict:
    """Extrai metadados do bloco YAML inicial (--- ... ---) sem depender de lib yaml."""
    m = re.match(r"^---\s*\n(.*?)\n---", md_text, re.S)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip("\"'")
    return meta


def discover_domains() -> dict:
    """Retorna {dir_name: {'name','description','path'}} para cada skill."""
    domains = {}
    if not SKILLS_ROOT.exists():
        return domains
    for child in sorted(SKILLS_ROOT.iterdir()):
        skill_file = child / "SKILL.md"
        if child.is_dir() and skill_file.exists():
            md = skill_file.read_text(encoding="utf-8", errors="ignore")
            meta = parse_frontmatter(md)
            domains[child.name] = {
                "name": meta.get("name") or child.name,
                "description": meta.get("description") or "",
                "path": str(skill_file),
            }
    return domains


def build_card(domain: str, info: dict, version: str = "1.0.0") -> dict:
    name = info["name"]
    desc = info["description"]
    return {
        "@context": "https://json-ld.org/contexts/person.jsonld",
        "object": "AgentCard",
        "name": name,
        "description": desc or f"Agente especialista {domain} da plataforma de agents da LigaCommerce.",
        "url": f"{BASE_URL}/{domain}",
        "provider": PROVIDER,
        "version": version,
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "stateTransitionHistory": True,
        },
        "authentication": {"schemes": ["none"]},
        "defaultInputModes": ["text/plain", "text/markdown"],
        "defaultOutputModes": ["text/plain", "text/markdown"],
        "skills": [{
            "id": domain,
            "name": name,
            "description": desc[:280],
            "tags": ["software-factory", domain],
        }],
        "security": {"apiKeys": False, "mcpServers": []},
        "source": info["path"].replace("\\", "/"),
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
    }


def write_cards(out_dir: Path, domains: dict) -> tuple:
    out_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for domain, info in domains.items():
        card = build_card(domain, info)
        target = out_dir / f"agent-card-{domain}.json"
        target.write_text(json.dumps(card, indent=2, ensure_ascii=False), encoding="utf-8")
        cards.append(card)
    index = {
        "index": "A2A Agent Cards — LigaCommerce",
        "count": len(cards),
        "generatedAt": datetime.now().isoformat(),
        "agents": [
            {"id": c["skills"][0]["id"], "name": c["name"], "card": f"agent-card-{c['skills'][0]['id']}.json"}
            for c in sorted(cards, key=lambda c: c["name"])
        ],
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return cards, index


def validate_cards(out_dir: Path) -> dict:
    report = {"valid": True, "checked": 0, "errors": []}
    for card_file in sorted(out_dir.glob("agent-card-*.json")):
        report["checked"] += 1
        try:
            card = json.loads(card_file.read_text(encoding="utf-8"))
            if card.get("object") != "AgentCard":
                report["errors"].append(f"{card_file.name}: object != AgentCard")
            if not card.get("name"):
                report["errors"].append(f"{card_file.name}: sem 'name'")
            if not card.get("skills"):
                report["errors"].append(f"{card_file.name}: sem 'skills'")
        except json.JSONDecodeError as e:
            report["errors"].append(f"{card_file.name}: JSON inválido ({e})")
    report["valid"] = not report["errors"]
    return report


def main():
    p = argparse.ArgumentParser(description="Gera/valida A2A Agent Cards a partir dos SKILL.md.")
    p.add_argument("--out", "-o", default="docs/agent-cards", help="Diretório de saída (default: docs/agent-cards)")
    p.add_argument("--validate", action="store_true", help="Apenas valida cards existentes")
    p.add_argument("--json", action="store_true", help="Saída em JSON")
    args = p.parse_args()

    out_dir = ROOT / args.out
    if args.validate:
        report = validate_cards(out_dir)
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(SEP)
            print("  🔖 A2A AGENT CARDS — validação")
            print(SEP)
            print(f"  Cards encontrados: {report['checked']}")
            if report["errors"]:
                for e in report["errors"]:
                    print(f"  ❌ {e}")
                print(SEP)
                print("  🔴 Cards INVÁLIDOS")
            else:
                print("  🟢 Todos os cards válidos conforme schema A2A v1.0")
            print(SEP)
        sys.exit(0 if report["valid"] else 1)

    domains = discover_domains()
    if not domains:
        print("[ERRO] Nenhum SKILL.md encontrado em .agents/skills/")
        sys.exit(1)

    cards, index = write_cards(out_dir, domains)
    if args.json:
        print(json.dumps({"generated": len(cards), "dir": str(out_dir)}, ensure_ascii=False))
    else:
        print(SEP)
        print("  🔖 A2A AGENT CARDS — GERADOS")
        print(SEP)
        print(f"  Skills catalogados: {len(domains)}")
        for domain in sorted(domains):
            print(f"     • {domain}")
        print(f"\n  📁 Saída: {out_dir}")
        print(f"  📇 Índice de descoberta: {out_dir / 'index.json'}")
        print(SEP + "\n")


if __name__ == "__main__":
    main()