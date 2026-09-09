#!/usr/bin/env python3
"""
project_context.py — Agent-OS agnóstico a projeto (SSOT de resolução de paths).

Problema original: scripts usavam `Path(__file__).parent.parent.parent` como ROOT,
o que resolve para `C:\\dev\\` quando `.agents` é junction para `C:\\dev\\agent-os`,
e hard-codavam coleções `antecipia_*`, dirs `antecipia-api/ui` e links
`file:///c:/dev/startup-AntecipIA/03_engineering/...`.

Solução: todo script deve resolver o PROJECT_ROOT a partir do CWD (projeto linkado),
derivar um slug estável e isolar dados por projeto em
`.agents/rag/knowledge/projects/<slug>/` e `.agents/memory/projects/<slug>/`,
mantendo fallback de leitura para o índice legado `antecipia_all`.

Uso:
    from project_context import get_project_root, get_agents_dir, get_project_slug
    from project_context import get_index_dir, get_project_memory_dir, collection_name
"""
import re
import sys
import unicodedata
from pathlib import Path

_THIS_FILE = Path(__file__).resolve()
_AGENTS_DIR_RESOLVED = _THIS_FILE.parent.parent  # C:\dev\agent-os (real, após junction)


def _normalize_slug(raw: str) -> str:
    # Remove acentos (Negócios -> negocios), minúsculas, troca não-alnum por _
    nfkd = unicodedata.normalize("NFKD", raw)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if len(slug) < 3:
        slug = (slug + "_proj").strip("_")
    return slug[:32]


def get_agents_dir() -> Path:
    """Diretório real do agent-os (alvo do junction .agents)."""
    return _AGENTS_DIR_RESOLVED


def get_project_root(start: Path | None = None) -> Path:
    """
    Resolve a raiz do PROJETO LINKADO (não do agent-os).

    Ordem:
    1. Do CWD para cima, o primeiro dir contendo `.agents/` (junction ou pasta).
    2. Se CWD já está dentro do agent-os standalone (contém skills/ + rag/),
       retorna o próprio CWD se ele for raiz, senão o agent-os root.
    3. Fallback: CWD.
    """
    cwd = Path(start) if start else Path.cwd()
    # Normaliza sem resolver junction cedo demais (preserva lógica do projeto)
    try:
        cwd_abs = cwd.resolve()
    except Exception:
        cwd_abs = cwd.absolute()

    # 1. Procura .agents subindo a partir do CWD lógico + resolvido
    candidates = []
    p = cwd
    for _ in range(10):
        candidates.append(p)
        if p.parent == p:
            break
        p = p.parent
    # Também tenta a partir do path resolvido (cobre junction)
    pr = cwd_abs
    for _ in range(10):
        if pr not in candidates:
            candidates.append(pr)
        if pr.parent == pr:
            break
        pr = pr.parent

    for base in candidates:
        try:
            if (base / ".agents").is_dir():
                return base
        except Exception:
            continue

    # 2. Standalone: estou dentro do agent-os?
    # Se o dir atual (ou algum pai até 4 níveis) contém skills/ + rag/, é o agent-os.
    probe = cwd_abs
    for _ in range(5):
        try:
            if (probe / "skills").is_dir() and (probe / "rag").is_dir():
                return probe
        except Exception:
            pass
        if probe.parent == probe:
            break
        probe = probe.parent

    # 3. Fallback
    return cwd_abs


def get_project_slug(project_root: Path | None = None) -> str:
    root = project_root or get_project_root()
    try:
        name = root.name
    except Exception:
        name = "proj"
    if not name or name in (".", "/"):
        return "proj"
    return _normalize_slug(name)


def get_index_dir(project_root: Path | None = None, agents_dir: Path | None = None) -> Path:
    """Índice RAG por projeto. Cria o diretório se necessário."""
    root = project_root or get_project_root()
    adir = agents_dir or get_agents_dir()
    slug = get_project_slug(root)
    d = adir / "rag" / "knowledge" / "projects" / slug
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def legacy_index_dir(agents_dir: Path | None = None) -> Path:
    adir = agents_dir or get_agents_dir()
    return adir / "rag" / "knowledge" / "project_index"


def get_project_memory_dir(project_root: Path | None = None, agents_dir: Path | None = None) -> Path:
    """Memória (snapshots, graph status) por projeto. Cria se necessário."""
    root = project_root or get_project_root()
    adir = agents_dir or get_agents_dir()
    slug = get_project_slug(root)
    d = adir / "memory" / "projects" / slug
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def collection_name(target: str, project_root: Path | None = None) -> str:
    """Nome de coleção Chroma por projeto. Compatível: [a-z0-9_-], 3-63 chars."""
    slug = get_project_slug(project_root)
    t = re.sub(r"[^a-z0-9_-]+", "_", target.lower()).strip("_") or "all"
    name = f"{slug}_{t}"[:60]
    # Chroma exige >=3 chars
    if len(name) < 3:
        name = (name + "_all")[:60]
    return name


def legacy_collection_name(target: str) -> str:
    t = re.sub(r"[^a-z0-9_-]+", "_", target.lower()).strip("_") or "all"
    return f"antecipia_{t}"[:60]


def discover_code_dirs(project_root: Path | None = None) -> dict:
    """
    Descobre dirs de código existentes no projeto (agnóstico).
    Retorna {target: [Path,...]} incluindo 'all' e 'agents'.
    """
    root = project_root or get_project_root()
    adir = get_agents_dir()
    candidates = ["app", "components", "lib", "src", "shared", "hooks", "docs", "scripts", "public"]
    out: dict = {}
    for c in candidates:
        p = root / c
        try:
            if p.is_dir():
                out[c] = [p]
        except Exception:
            continue
    out["agents"] = []
    for sub in (adir / "skills", adir / "scripts"):
        try:
            if sub.is_dir():
                out["agents"].append(sub)
        except Exception:
            continue
    # all = união de tudo (só paths existentes)
    seen = []
    for _k, paths in out.items():
        if _k == "all":
            continue
        for pp in paths:
            if pp not in seen:
                seen.append(pp)
    out["all"] = seen
    return out


if __name__ == "__main__":
    import json
    root = get_project_root()
    adir = get_agents_dir()
    info = {
        "project_root": str(root),
        "agents_dir": str(adir),
        "project_slug": get_project_slug(root),
        "index_dir": str(get_index_dir(root, adir)),
        "legacy_index_dir": str(legacy_index_dir(adir)),
        "project_memory_dir": str(get_project_memory_dir(root, adir)),
        "collection_all": collection_name("all", root),
    }
    print(json.dumps(info, indent=2, ensure_ascii=False))
