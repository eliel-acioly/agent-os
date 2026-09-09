#!/usr/bin/env python3
"""
check_mcp.py — Diagnóstico e Validação de Servidores MCP (padrão Model Context Protocol 2026)
Analisa .agents/mcp_config.json e .agents/mcp_config.modern.json:
  - lista servidores (remote URL vs stdio local vs npx)
  - verifica presença de arquivos locais
  - sinaliza valores fixos inseguros que devem ser trocados por variáveis ${ENV}
  - gera recomendação de ativação gradual (read-only → repo → escrita)

Uso:
  python .agents/scripts/check_mcp.py
  python .agents/scripts/check_mcp.py --json
"""

import sys
import os
import json
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from project_context import get_project_root, get_agents_dir, get_project_slug

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
# mcp_config vive no agent-os (alvo do junction), com override opcional por projeto
CONFIGS = [
    AGENTS_DIR / "mcp_config.json",
    AGENTS_DIR / "mcp_config.modern.json",
    PROJECT_ROOT / "mcp_config.json",
]
ROOT = PROJECT_ROOT
SEP = "=" * 70

INSECURE_VALUE_HINTS = ["sua-", "seu-", "changeme", "example", "xxxx", "token-aqui", "pat-aqui"]


def analyze_config(path: Path) -> dict:
    try:
        label = str(path.relative_to(ROOT))
    except ValueError:
        # Config vive no agent-os (fora do projeto linkado): exibe nome + origem
        try:
            label = str(path.relative_to(AGENTS_DIR))
            label = f".agents/{label}"
        except ValueError:
            label = str(path)
    result = {"config": label, "servers": [], "warnings": []}
    if not path.exists():
        result["missing"] = True
        return result
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result["invalid"] = str(e)
        return result

    result["missing"] = False
    for name, spec in (data.get("mcpServers") or {}).items():
        entry = {"name": name}
        if spec.get("serverUrl"):
            entry["type"] = "remote-url"
            entry["url"] = spec["serverUrl"]
        elif spec.get("command"):
            entry["type"] = "stdio"
            entry["command"] = spec.get("command")
            entry["args"] = spec.get("args") or []
            cmd = spec.get("command")
            if cmd not in ("npx", "node", "python", "uvx", "bunx"):
                local = PROJECT_ROOT / cmd
                entry["local_file_exists"] = local.exists()
            elif cmd == "node":
                # scripts/mcp-*.js do projeto linkado
                args = spec.get("args") or []
                candidate = None
                for a in args:
                    if isinstance(a, str) and a.endswith(".js"):
                        candidate = a
                        break
                if candidate:
                    entry["local_file_exists"] = (PROJECT_ROOT / candidate).exists()
                    entry["local_file"] = candidate
        entry["enabled"] = spec.get("enabled", True)
        env = [k for k in (spec.get("env") or {}).keys()]
        entry["env_keys"] = env
        # Valores fixos potencialmente inseguros
        insecure = []
        for k, v in (spec.get("env") or {}).items():
            vs = str(v).lower()
            if any(hint in vs for hint in INSECURE_VALUE_HINTS) or "${" not in v:
                insecure.append(k)
        for a in (spec.get("args") or []):
            if "postgresql://" in a.lower():
                entry["has_db_url_in_args"] = True
        if insecure:
            entry["insecure_env_values"] = insecure
            result["warnings"].append(f"[{name}] troque valores fixos por ${insecure[0]}")
        result["servers"].append(entry)
    return result


def main():
    p = argparse.ArgumentParser(description="check_mcp — diagnóstico dos servidores MCP configurados.")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    reports = [analyze_config(c) for c in CONFIGS]
    if args.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
        return

    print(SEP)
    print("  CHECK MCP — DIAGNÓSTICO DE SERVIDORES")
    print(f"  Projeto: {PROJECT_SLUG} ({PROJECT_ROOT})")
    print(SEP)
    for r in reports:
        rel = r.get("config", "?")
        if r.get("missing"):
            print(f"\n  ⚠️  {rel}: arquivo não encontrado (opcional/opt-in).")
            continue
        if r.get("invalid"):
            print(f"\n  🔴 {rel}: JSON inválido -> {r['invalid']}")
            continue
        if not r["servers"]:
            print(f"\n  ⚠️  {rel}: sem servidores configurados.")
            continue
        print(f"\n  📄 {rel} ({len(r['servers'])} servidor(es))")
        for s in r["servers"]:
            tag = "🟢 ativo" if s.get("enabled") else "🔵 opt-in"
            print(f"     • {tag} {s['name']} [{s['type']}]")
            if s["type"] == "remote-url":
                print(f"         url: {s.get('url')}")
            if s["type"] == "stdio":
                cmd = f"{s.get('command')} {' '.join(s.get('args', []))}"
                print(f"         cmd: {cmd}")
                if "local_file_exists" in s:
                    print(f"         arquivo local presente: {s['local_file_exists']}")
            if s.get("env_keys"):
                print(f"         env keys: {', '.join(s['env_keys'])}")
            if s.get("insecure_env_values"):
                print(f"         ⚠️  valores fixos (trocar por ${{ENV}}): {', '.join(s['insecure_env_values'])}")
            if s.get("has_db_url_in_args"):
                print(f"         ⚠️  DATABASE_URL direto nos args (mover para env/secret)")
        for w in r["warnings"]:
            print(f"  ⚠️  {w}")

    print(SEP)
    print("  ✅ RECOMENDAÇÃO DE ATIVAÇÃO GRADUAL (segurança)")
    print("     1. postgres-connect (somente leitura)  → 2. github-official (repo)  → 3. supabase (escrita)")
    print("     Regra: nunca exponha SERVICE_ROLE em args/env fixos; use variáveis ${ENV}.")
    print(SEP + "\n")


if __name__ == "__main__":
    main()