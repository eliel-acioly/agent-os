#!/usr/bin/env python3
"""
blast_radius.py — Blast Radius & Impact Mapping (agnóstico a projeto, padrão SWE-agent ACI)
Calcula o raio de impacto (até N saltos) de um arquivo/símbolo usando o grafo de imports:
  - Salto 1: importadores diretos
  - Salto 2: importadores dos importadores (transitivo)
  - Salto N: expansão até o limite configurado
Classifica os impactados (UI, API_ROUTE, TEST, LIB, APP) e destaca hubs (ex: lib/types.ts = SSOT).

Uso:
  python .agents/scripts/blast_radius_lc.py --file lib/types.ts
  python .agents/scripts/blast_radius_lc.py --file components/showcase/ProductDetailModal.tsx --hops 2
  python .agents/scripts/blast_radius_lc.py --top --limit 10
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from project_context import get_project_root, get_agents_dir, get_project_slug, discover_code_dirs

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
ROOT = PROJECT_ROOT
_discovered = discover_code_dirs(PROJECT_ROOT)
SCAN_DIRS = [k for k in ("app", "components", "lib", "src", "shared", "hooks", "scripts") if k in _discovered]
VALID_EXTS = (".ts", ".tsx", ".js", ".jsx")
SKIP = {"node_modules", ".next", "dist", "build", ".git", "__pycache__", ".agents", "docs", ".venv"}
SEP = "=" * 70
IMPORT_RE = re.compile(r"(?:from|import)\s+['\"]([^'\"]+)['\"]")


def load_files() -> dict:
    files = {}
    for d in SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [x for x in dns if x not in SKIP]
            for fn in fns:
                if fn.endswith(VALID_EXTS):
                    fp = Path(dp) / fn
                    files[fp.relative_to(ROOT).as_posix()] = fp
    return files


def resolve_import(source_rel: str, imp: str, files: dict):
    if imp.startswith("@/"):
        base = imp[2:]
    elif imp.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(source_rel), imp)).replace("\\", "/")
    else:
        return None
    if base in files:
        return base
    for ext in VALID_EXTS:
        if base + ext in files:
            return base + ext
    for ext in VALID_EXTS:
        idx = base + "/index" + ext
        if idx in files:
            return idx
    return None


def build_importers():
    files = load_files()
    importers = defaultdict(set)
    for rel, fp in files.items():
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in IMPORT_RE.finditer(text):
            target = resolve_import(rel, m.group(1), files)
            if target and target != rel:
                importers[target].add(rel)
    return files, importers


def blast_radius(seed: str, importers: dict, hops: int) -> dict:
    radius = {1: importers.get(seed, set())}
    frontier = set(radius[1])
    visited = set(seed) | set(frontier)
    for h in range(2, hops + 1):
        nxt = set()
        for f in frontier:
            nxt |= importers.get(f, set())
        nxt -= visited
        radius[h] = nxt
        visited |= nxt
        frontier = nxt
    return radius


def classify(rel: str) -> str:
    if rel.startswith("app/api/"):
        return "API_ROUTE"
    if "test" in rel.split("/")[-1].lower():
        return "TEST"
    if rel.startswith("components/"):
        return "UI"
    if rel.startswith("lib/"):
        return "LIB"
    if rel.startswith("scripts/"):
        return "SCRIPT"
    if rel.startswith("app/"):
        return "APP"
    return "OTHER"


def main():
    p = argparse.ArgumentParser(description="Blast Radius real por projeto (grafo de imports).")
    p.add_argument("--file", "-f", help="Arquivo-alvo (ex: lib/types.ts) para calcular raio de impacto")
    p.add_argument("--hops", type=int, default=3, help="Número de saltos (1-5)")
    p.add_argument("--top", action="store_true", help="Lista hubs por centralidade (in-degree)")
    p.add_argument("--limit", type=int, default=12)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    files, importers = build_importers()

    if args.top:
        ranking = sorted(importers.items(), key=lambda kv: len(kv[1]), reverse=True)[: args.limit]
        if args.json:
            print(json.dumps(
                [{"file": f, "importers": len(s), "is_hub": len(s) >= 3} for f, s in ranking],
                indent=2, ensure_ascii=False))
        else:
            print(SEP)
            print(f"  TOP HUBS DE DEPENDÊNCIA — {PROJECT_SLUG}")
            print(SEP)
            for i, (f, s) in enumerate(ranking, 1):
                hub = "🌟 HUB CENTRAL" if len(s) >= 3 else ""
                print(f"  {i:>2}. {f} ({len(s)} importadores) {hub}")
            print(SEP)
        return

    seed = args.file
    if not seed:
        p.print_help()
        return
    if seed not in files:
        print(f"[ERRO] Arquivo não encontrado no grafo: '{seed}'")
        print("       Índice cobre: lib/, components/, app/, scripts/")
        sys.exit(1)

    radius = blast_radius(seed, importers, args.hops)
    total = sum(len(v) for v in radius.values())

    if args.json:
        print(json.dumps({
            "seed": seed,
            "total_affected": total,
            "hops": {str(h): sorted(s) for h, s in radius.items()},
        }, indent=2, ensure_ascii=False))
    else:
        print(SEP)
        print(f"  💥 BLAST RADIUS — {seed}")
        print(SEP)
        for h in range(1, args.hops + 1):
            s = radius.get(h, set())
            print(f"\n  Salto {h} ({len(s)} arquivo(s)):")
            for rel in sorted(s):
                print(f"     • [{classify(rel):>10}] {rel}")
            api_hits = [r for r in s if classify(r) == "API_ROUTE"]
            test_hits = [r for r in s if classify(r) == "TEST"]
            if api_hits:
                print(f"     ⚠️  Rotas de API atingidas: {', '.join(api_hits)}")
            if test_hits:
                print(f"     🧪 Testes relacionados: {', '.join(test_hits)}")
        print(SEP)
        print(f"  Total afetado (transitivo, {args.hops} saltos): {total} arquivos")
        print(SEP)


if __name__ == "__main__":
    main()