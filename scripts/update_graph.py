#!/usr/bin/env python3
"""
update_graph.py — Agent-OS (agnóstico a projeto)
Verifica e registra snapshot do PROJETO LINKADO (raiz com `.agents/`).
O snapshot por projeto vive em `.agents/memory/projects/<slug>/`.
Uso: python .agents/scripts/update_graph.py [--target app|components|lib|docs|scripts|all]
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

sys.path.insert(0, str(Path(__file__).parent))
from project_context import (
    get_project_root, get_agents_dir, get_project_slug,
    get_project_memory_dir, discover_code_dirs,
)

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
MEMORY_DIR = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR)
LEGACY_MEMORY_DIR = AGENTS_DIR / "memory"
GRAPH_STATUS_FILE = MEMORY_DIR / "graph_last_updated.json"
GRAPH_DB = PROJECT_ROOT / ".code-review-graph" / "graph.db"

SEPARATOR = "═" * 65


def _build_submodule_dirs() -> dict:
    found = discover_code_dirs(PROJECT_ROOT)
    # update_graph espera {target: Path}; discover retorna {target: [Path,...]}
    out: dict = {}
    for key, paths in found.items():
        if key in ("agents", "all"):
            continue
        if paths:
            out[key] = paths[0]
    out["root"] = PROJECT_ROOT
    return out


SUBMODULE_DIRS = _build_submodule_dirs()


def get_git_head(repo_dir: Path) -> str:
    """Retorna o hash HEAD atual do repositório git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def get_git_status(repo_dir: Path) -> list:
    """Retorna lista de arquivos modificados desde o último commit."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return [l.strip() for l in result.stdout.splitlines() if l.strip()]
        return []
    except Exception:
        return []


def load_status() -> dict:
    if GRAPH_STATUS_FILE.exists():
        return json.loads(GRAPH_STATUS_FILE.read_text(encoding="utf-8"))
    return {}


def save_status(status: dict):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    GRAPH_STATUS_FILE.write_text(
        json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def check_needs_rebuild(target: str, current_head: str) -> bool:
    """Verifica se o grafo precisa ser reconstruído comparando com o HEAD anterior."""
    status = load_status()
    last_head = status.get(target, {}).get("last_head", "")
    return current_head != last_head


def try_rebuild_graph(target: str, repo_dir: Path) -> bool:
    """
    Tenta acionar o rebuild do code-review-graph.
    Retorna True se bem-sucedido, False se não disponível.
    """
    # Verificar se o comando code-review-graph está disponível
    for cmd in ["code-review-graph", "crg", "npx code-review-graph"]:
        try:
            result = subprocess.run(
                cmd.split() + ["build", "--path", str(repo_dir)],
                capture_output=True, text=True, timeout=120,
                cwd=str(PROJECT_ROOT)
            )
            if result.returncode == 0:
                print(f"[OK] Grafo rebuilt para {target}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return False


def generate_code_summary(target: str, repo_dir: Path) -> dict:
    """
    Gera um resumo estatístico do codebase como fallback quando o grafo não está disponível.
    """
    summary = {
        "target": target,
        "project": PROJECT_SLUG,
        "path": str(repo_dir),
        "file_counts": {},
        "recent_changes": []
    }

    if not repo_dir.exists():
        return summary

    extensions = {".ts": 0, ".tsx": 0, ".py": 0, ".go": 0, ".proto": 0, ".json": 0}
    for ext in extensions:
        try:
            count = 0
            for f in repo_dir.rglob(f"*{ext}"):
                try:
                    if not any(part in f.parts for part in ["node_modules", "venv", "__pycache__", "dist", ".git"]):
                        count += 1
                except Exception:
                    continue
            extensions[ext] = count
        except Exception:
            extensions[ext] = -1  # Indica erro de acesso

    summary["file_counts"] = extensions

    # Arquivos modificados recentemente
    changes = get_git_status(repo_dir)
    summary["recent_changes"] = changes[:10]

    return summary


def main():
    parser = argparse.ArgumentParser(description="Atualiza o code-review-graph do projeto.")
    parser.add_argument("--target", "-t", choices=list(SUBMODULE_DIRS.keys()) + ["all"],
                        default="all", help="Submódulo alvo para rebuild")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Forçar rebuild mesmo sem mudanças detectadas")
    args = parser.parse_args()

    targets = list(SUBMODULE_DIRS.keys()) if args.target == "all" else [args.target]

    print(f"\n{SEPARATOR}")
    print(f"  code-review-graph Auto-Update — Agent-OS (projeto: {PROJECT_SLUG})")
    print(f"  Root: {PROJECT_ROOT}")
    print(f"  Targets: {', '.join(targets)}")
    print(SEPARATOR)

    status = load_status()
    any_updated = False

    for target in targets:
        repo_dir = SUBMODULE_DIRS[target]
        current_head = get_git_head(repo_dir)
        needs_rebuild = args.force or check_needs_rebuild(target, current_head)
        changes = get_git_status(repo_dir)

        print(f"\n  🔍 {target}")
        print(f"     HEAD: {current_head}")
        print(f"     Mudanças locais: {len(changes)} arquivo(s)")

        if not needs_rebuild:
            print(f"     Status: ✅ Grafo atualizado (HEAD não mudou)")
            continue

        print(f"     Status: 🔄 Rebuild necessário...")
        rebuilt = try_rebuild_graph(target, repo_dir)

        if not rebuilt:
            print(f"     ⚠️  code-review-graph CLI não disponível — gerando snapshot estático")
            summary = generate_code_summary(target, repo_dir)
            summary["generated_at"] = datetime.now().isoformat()
            snapshot_file = MEMORY_DIR / f"snapshot_{target}.json"
            snapshot_file.parent.mkdir(parents=True, exist_ok=True)
            snapshot_file.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"     [OK] Snapshot salvo em: {snapshot_file.name}")

        # Atualizar status
        status[target] = {
            "last_head": current_head,
            "last_updated": datetime.now().isoformat(),
            "rebuilt": rebuilt,
            "changes_detected": len(changes)
        }
        any_updated = True

    save_status(status)

    print(f"\n{SEPARATOR}")
    if any_updated:
        print("  ✅ Grafo de código atualizado. Sistema pronto para novas sessões.")
    else:
        print("  ✅ Todos os grafos estão em dia. Nenhuma ação necessária.")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    main()
