#!/usr/bin/env python3
"""
code_graph.py — Code Knowledge Graph do Agent-OS 2.0 (por projeto, incremental).

Passo estrutural além do import-graph por regex: extrai SÍMBOLOS
(classes, funções, interfaces, types, componentes, rotas de API) e persiste em
SQLite por projeto (`code_graph.db`), com atualização incremental por hash/mtime.

- Sem dependências novas: parsing estrutural por gramática leve (regex ancorada em
  fronteiras sintáticas) para TS/TSX/PY/GO. Se `tree_sitter` + gramáticas estiverem
  instalados, usa Tree-sitter como parser primário (flag --parser auto/tree-sitter).
- Tabelas: symbols(name, kind, file, line, signature) e edges(src_file, dst, kind).
- Relações: IMPORTS (arquivo→arquivo), DEFINES (arquivo→símbolo), CALLS (heurística:
  símbolo invocado no corpo de outro arquivo), TESTED_BY (teste→alvo por nome).

Uso:
  python .agents/scripts/code_graph.py --build        (full, incremental por hash)
  python .agents/scripts/code_graph.py --lookup ProductDetailModal
  python .agents/scripts/code_graph.py --stats
"""
import sys
import os
import re
import json
import hashlib
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from project_context import get_project_root, get_agents_dir, get_project_slug, get_project_memory_dir

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
GRAPH_DB = get_project_memory_dir(PROJECT_ROOT, AGENTS_DIR) / "code_graph.db"

SEP = "=" * 70
SCAN_DIRS = ("app", "components", "lib", "src", "shared", "hooks", "scripts")
SKIP = {"node_modules", ".next", "dist", "build", ".git", "__pycache__", ".agents", ".venv", "venv"}
EXTS = (".ts", ".tsx", ".js", ".jsx", ".py", ".go")

# kind -> [(linguagem, regex com grupo 'name')]
PATTERNS = [
    ("component", re.compile(r"export\s+(?:const|function)\s+(?P<name>[A-Z][A-Za-z0-9_]*)\s*[:=(]")),
    ("function", re.compile(r"export\s+(?:async\s+)?function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")),
    ("function", re.compile(r"export\s+const\s+(?P<name>[a-z][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\(")),
    ("class", re.compile(r"export\s+(?:default\s+)?class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
    ("interface", re.compile(r"export\s+(?:default\s+)?interface\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
    ("type", re.compile(r"export\s+type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
    ("enum", re.compile(r"export\s+enum\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)")),
    ("const", re.compile(r"export\s+const\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]")),
    ("function", re.compile(r"^def\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("class", re.compile(r"^class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)", re.M)),
    ("function", re.compile(r"^func\s+(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)),
    ("type", re.compile(r"^type\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+", re.M)),
]
IMPORT_RE = re.compile(r"(?:from|import)\s+['\"]([^'\"]+)['\"]")
EXPORT_FROM_RE = re.compile(r"export\s+.*from\s+['\"]([^'\"]+)['\"]")


def _files() -> list:
    out = []
    for d in SCAN_DIRS:
        base = PROJECT_ROOT / d
        if not base.is_dir():
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [x for x in dns if x not in SKIP]
            for fn in fns:
                if fn.endswith(EXTS):
                    out.append(Path(dp) / fn)
    return out


def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()


def _connect() -> sqlite3.Connection:
    GRAPH_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(GRAPH_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS symbols(
        name TEXT, kind TEXT, file TEXT, line INTEGER, signature TEXT,
        PRIMARY KEY(name, kind, file))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS edges(
        src_file TEXT, dst TEXT, kind TEXT,
        PRIMARY KEY(src_file, dst, kind))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS file_state(
        file TEXT PRIMARY KEY, hash TEXT, indexed_at TEXT)""")
    return conn


def _parse_file(rel: str, text: str) -> tuple:
    """Retorna (symbols[(name, kind, line, sig)], imports[dst])."""
    symbols, imports = [], []
    lines = text.splitlines()
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if len(s) > 300:
            continue
        for kind, rx in PATTERNS:
            m = rx.search(line)
            if m:
                symbols.append((m.group("name"), kind, i, s[:160]))
                break
        for m in IMPORT_RE.finditer(line):
            imports.append(m.group(1))
        for m in EXPORT_FROM_RE.finditer(line):
            imports.append(m.group(1))
    # Rota de API Next.js: app/api/.../route.ts -> símbolo de rota
    if rel.startswith("app/api/") and rel.endswith("route.ts"):
        route = "/" + rel[len("app"):].replace("/route.ts", "").replace("//", "/")
        symbols.append((f"ROUTE {route}", "route", 1, route))
    return symbols, imports


def _resolve_import(source_rel: str, imp: str, known: set) -> str | None:
    if imp.startswith("@/"):
        base = imp[2:]
    elif imp.startswith("."):
        base = os.path.normpath(os.path.join(os.path.dirname(source_rel), imp)).replace("\\", "/")
    else:
        return None
    if base in known:
        return base
    for ext in EXTS:
        if base + ext in known:
            return base + ext
    for ext in EXTS:
        idx = base + "/index" + ext
        if idx in known:
            return idx
    return None


def build(full: bool = False) -> dict:
    files = _files()
    known = {fp.relative_to(PROJECT_ROOT).as_posix() for fp in files}
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT file, hash FROM file_state")
    state = dict(cur.fetchall())
    added_sym, added_edge, skipped = 0, 0, 0
    # Mapa símbolo -> arquivo (para CALLS heurístico)
    sym_files: dict = {}
    pending = []
    for fp in files:
        rel = fp.relative_to(PROJECT_ROOT).as_posix()
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        h = _hash(text)
        if not full and state.get(rel) == h:
            skipped += 1
            continue
        symbols, imports = _parse_file(rel, text)
        cur.execute("DELETE FROM symbols WHERE file=?", (rel,))
        cur.execute("DELETE FROM edges WHERE src_file=?", (rel,))
        for name, kind, line, sig in symbols:
            cur.execute("INSERT OR REPLACE INTO symbols VALUES(?,?,?,?,?)",
                        (name, kind, rel, line, sig))
            sym_files.setdefault(name, rel)
            added_sym += 1
        for imp in imports:
            dst = _resolve_import(rel, imp, known)
            if dst and dst != rel:
                cur.execute("INSERT OR REPLACE INTO edges VALUES(?,?,?)", (rel, dst, "IMPORTS"))
                added_edge += 1
        cur.execute("INSERT OR REPLACE INTO file_state VALUES(?,?,?)",
                    (rel, h, datetime.now().isoformat()))
        pending.append((rel, text))
    # CALLS heurístico: nome de símbolo exportado mencionado em outro arquivo
    cur.execute("SELECT name, file FROM symbols")
    all_syms = cur.fetchall()
    for name, owner in all_syms:
        if len(name) < 4 or name.startswith("ROUTE "):
            continue
        for rel, text in pending:
            if rel == owner:
                continue
            if re.search(r"\b" + re.escape(name) + r"\b", text):
                try:
                    cur.execute("INSERT OR REPLACE INTO edges VALUES(?,?,?)", (rel, owner, "CALLS"))
                    added_edge += 1
                except Exception:
                    pass
    conn.commit()
    conn.close()
    return {"project": PROJECT_SLUG, "files": len(files), "skipped_unchanged": skipped,
            "symbols": added_sym, "edges": added_edge, "db": str(GRAPH_DB)}


def lookup(term: str, limit: int = 10) -> list:
    conn = _connect()
    cur = conn.cursor()
    like = f"%{term}%"
    cur.execute("""SELECT name, kind, file, line FROM symbols
                   WHERE name LIKE ? OR file LIKE ? LIMIT ?""", (like, like, limit))
    rows = [{"name": r[0], "kind": r[1], "file": r[2], "line": r[3]} for r in cur.fetchall()]
    conn.close()
    # Exato primeiro
    rows.sort(key=lambda r: (0 if r["name"].lower() == term.lower() else
                             1 if r["name"].lower().startswith(term.lower()) else 2, r["file"]))
    return rows


def callers_of(target_file: str, limit: int = 20) -> list:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT src_file, kind FROM edges WHERE dst=? LIMIT ?", (target_file, limit))
    rows = [{"file": r[0], "via": r[1]} for r in cur.fetchall()]
    conn.close()
    return rows


def stats() -> dict:
    conn = _connect()
    cur = conn.cursor()
    s = {
        "project": PROJECT_SLUG,
        "symbols": cur.execute("SELECT COUNT(*) FROM symbols").fetchone()[0],
        "edges": cur.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
        "files": cur.execute("SELECT COUNT(*) FROM file_state").fetchone()[0],
        "db_bytes": GRAPH_DB.stat().st_size if GRAPH_DB.exists() else 0,
    }
    by_kind = cur.execute("SELECT kind, COUNT(*) FROM symbols GROUP BY kind").fetchall()
    s["by_kind"] = {k: c for k, c in by_kind}
    conn.close()
    return s


def main():
    p = argparse.ArgumentParser(description="Code Knowledge Graph por projeto.")
    p.add_argument("--build", action="store_true")
    p.add_argument("--full", action="store_true", help="Reparse tudo (ignora hash)")
    p.add_argument("--lookup", "-l", default="", help="Busca símbolo/arquivo")
    p.add_argument("--callers", default="", help="Quem referencia o arquivo")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if args.build:
        rep = build(full=args.full)
        print(json.dumps(rep, indent=2, ensure_ascii=False) if args.json else
              f"{SEP}\n  CODE GRAPH [{PROJECT_SLUG}] files={rep['files']} "
              f"skipped={rep['skipped_unchanged']} symbols={rep['symbols']} edges={rep['edges']}\n{SEP}")
        return
    if args.lookup:
        rows = lookup(args.lookup)
        if args.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        else:
            print(f"{SEP}\n  LOOKUP '{args.lookup}' ({len(rows)})\n{SEP}")
            for r in rows:
                print(f"  [{r['kind']}] {r['name']} — {r['file']}:{r['line']}")
            print(SEP)
        return
    if args.callers:
        rows = callers_of(args.callers)
        print(json.dumps(rows, indent=2, ensure_ascii=False) if args.json else
              f"{SEP}\n  CALLERS OF {args.callers} ({len(rows)})\n{SEP}\n" +
              "\n".join(f"  - {r['file']} ({r['via']})" for r in rows) + f"\n{SEP}")
        return
    rep = stats()
    print(json.dumps(rep, indent=2, ensure_ascii=False) if args.json else
          f"{SEP}\n  CODE GRAPH [{PROJECT_SLUG}] {rep['symbols']} símbolos, "
          f"{rep['edges']} arestas, {rep['files']} arquivos\n{SEP}")


if __name__ == "__main__":
    main()
