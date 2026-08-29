#!/usr/bin/env python3
"""
update_graph.py — AntecipIA Agent Platform v2.0
Verifica e rebuilda o code-review-graph para o submódulo alvo.
O grafo DEVE estar sempre atualizado antes de qualquer sessão de agente.
Uso: python .agents/scripts/update_graph.py [--target antecipia-api|antecipia-ui|all]
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

ROOT = Path(__file__).parent.parent.parent
MEMORY_DIR = Path(__file__).parent.parent / "memory"
GRAPH_STATUS_FILE = MEMORY_DIR / "graph_last_updated.json"
GRAPH_DB = ROOT / ".code-review-graph" / "graph.db"

SEPARATOR = "═" * 65

SUBMODULE_DIRS = {
    "antecipia-api": ROOT / "antecipia-api",
    "antecipia-ui":  ROOT / "antecipia-ui",
    "root":          ROOT,
}


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
                cwd=str(ROOT)
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
    print("  📊 code-review-graph Auto-Update — AntecipIA Platform v2.0")
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
