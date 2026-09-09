#!/usr/bin/env python3
"""
indexer.py — Agent-OS RAG Layer (agnóstico a projeto)
Indexa o codebase do PROJETO LINKADO (raiz com `.agents/`) em vector store ChromaDB.
Uso: python .agents/rag/indexer.py [--target all|app|components|lib|docs|scripts|agents]
"""

import sys
import os
import time
import gc
import hashlib
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

# Contexto agnóstico: PROJECT_ROOT = projeto linkado, AGENTS_DIR = agent-os real
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from project_context import (
    get_project_root, get_agents_dir, get_project_slug,
    get_index_dir, legacy_index_dir, collection_name, legacy_collection_name,
    discover_code_dirs,
)

PROJECT_ROOT = get_project_root()
AGENTS_DIR = get_agents_dir()
PROJECT_SLUG = get_project_slug(PROJECT_ROOT)
RAG_DIR = AGENTS_DIR / "rag"
INDEX_DIR = get_index_dir(PROJECT_ROOT, AGENTS_DIR)
LEGACY_INDEX_DIR = legacy_index_dir(AGENTS_DIR)

SEPARATOR = "═" * 65

# Extensões indexadas e seus pesos de relevância
INDEXED_EXTENSIONS = {
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".py": "Python",
    ".go": "Go",
    ".proto": "Protocol Buffers",
    ".sql": "SQL",
    ".md": "Markdown Documentation",
}

# Padrões excluídos
EXCLUDE_PATTERNS = [
    "node_modules", "venv", "__pycache__", "dist", ".git",
    "build", ".next", "generated", "migrations", "vllm_providers/__pycache__"
]

# Diretórios de código por alvo (descoberta dinâmica, agnóstica ao projeto)
def _build_target_dirs() -> dict:
    found = discover_code_dirs(PROJECT_ROOT)
    # Garante chaves estáveis mesmo se o dir não existir no projeto atual
    for key in ("app", "components", "lib", "docs", "scripts", "agents", "all"):
        found.setdefault(key, [])
    return found


TARGET_DIRS = _build_target_dirs()


def should_exclude(path: Path) -> bool:
    return any(part in path.parts for part in EXCLUDE_PATTERNS)


def chunk_code(content: str, file_path: str, chunk_size: int = 800) -> list:
    """
    Divide o conteúdo de um arquivo em chunks semânticos de tamanho controlado.
    Tenta dividir em fronteiras naturais (funções, classes, exports).
    """
    lines = content.splitlines()
    chunks = []
    current_chunk = []
    current_size = 0

    for i, line in enumerate(lines):
        current_chunk.append(line)
        current_size += len(line)

        # Divide em fronteira semântica natural
        is_boundary = (
            line.strip().startswith("export ")
            or line.strip().startswith("def ")
            or line.strip().startswith("func ")
            or line.strip().startswith("class ")
            or line.strip().startswith("// ---")
            or line.strip().startswith("## ")
        )

        if current_size >= chunk_size or (is_boundary and current_size > 200):
            chunk_text = "\n".join(current_chunk).strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "source": file_path,
                    "start_line": i - len(current_chunk) + 1,
                    "end_line": i + 1
                })
            current_chunk = []
            current_size = 0

    # Último chunk restante
    if current_chunk:
        chunk_text = "\n".join(current_chunk).strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "source": file_path,
                "start_line": len(lines) - len(current_chunk),
                "end_line": len(lines)
            })

    return chunks


def get_chroma_client():
    """Inicializa ChromaDB com persistência local."""
    try:
        import chromadb
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(INDEX_DIR))
        return client
    except ImportError:
        print("[ERRO] ChromaDB não instalado. Execute: pip install chromadb")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Indexa o codebase do projeto linkado no RAG ChromaDB.")
    parser.add_argument("--target", "-t",
                        choices=list(TARGET_DIRS.keys()),
                        default="all", help="Alvo de indexação")
    parser.add_argument("--reset", "-r", action="store_true",
                        help="Reinicia a coleção antes de indexar (re-indexação completa)")
    args = parser.parse_args()

    print(f"\n{SEPARATOR}")
    print(f"  RAG Indexer — ChromaDB (projeto: {PROJECT_SLUG})")
    print(f"  Target: {args.target.upper()}")
    print(f"  Root: {PROJECT_ROOT}")
    print(f"  Index: {INDEX_DIR}")
    print(SEPARATOR)

    client = get_chroma_client()
    coll_name = collection_name(args.target, PROJECT_ROOT)

    if args.reset:
        try:
            client.delete_collection(coll_name)
            print(f"[INFO] Coleção '{coll_name}' removida para re-indexação.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=coll_name,
        metadata={"description": f"{PROJECT_SLUG} codebase — {args.target}", "hnsw:space": "cosine"}
    )

    # Coletar arquivos de forma segura (sem entrar em node_modules/venv/etc.)
    search_dirs = TARGET_DIRS.get(args.target, [])
    all_files = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            print(f"[AVISO] Diretório não encontrado: {search_dir}")
            continue
        
        for root_path, dirs, filenames in os.walk(str(search_dir), topdown=True, followlinks=False):
            # Prune excluded directories in-place so os.walk does not traverse them
            dirs[:] = [d for d in dirs if not any(pat in d.lower() for pat in EXCLUDE_PATTERNS)]
            
            for fname in filenames:
                file_ext = Path(fname).suffix.lower()
                if file_ext in INDEXED_EXTENSIONS:
                    full_p = Path(root_path) / fname
                    if not should_exclude(full_p):
                        all_files.append(full_p)

    print(f"\n  📁 Arquivos encontrados: {len(all_files)}")

    # Indexar em batches consolidados
    BATCH_SIZE = 100
    total_chunks = 0
    indexed_files = 0

    batch_ids = []
    batch_docs = []
    batch_metas = []

    def flush_batch():
        nonlocal batch_ids, batch_docs, batch_metas, total_chunks
        if batch_ids:
            collection.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)
            total_chunks += len(batch_ids)
            batch_ids = []
            batch_docs = []
            batch_metas = []

    for i, file_path in enumerate(all_files):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content.strip()) < 20:
                continue

            try:
                rel_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
            except ValueError:
                # Arquivo do agent-os (skills/scripts): relativiza pelo AGENTS_DIR
                try:
                    rel_path = ".agents/" + str(file_path.relative_to(AGENTS_DIR)).replace("\\", "/")
                except ValueError:
                    rel_path = file_path.name
            chunks = chunk_code(content, rel_path)

            if not chunks:
                continue

            for j, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{rel_path}:{j}:{chunk['text'][:50]}".encode()).hexdigest()
                batch_ids.append(chunk_id)
                batch_docs.append(chunk["text"])
                batch_metas.append({
                    "source": chunk["source"].replace("\\", "/"),
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "file_type": INDEXED_EXTENSIONS.get(file_path.suffix, "Unknown"),
                    "indexed_at": datetime.now().isoformat()
                })

                if len(batch_ids) >= BATCH_SIZE:
                    flush_batch()

            indexed_files += 1

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(all_files)}] {indexed_files} arquivos processados, {total_chunks + len(batch_ids)} chunks acumulados...")

        except Exception as e:
            print(f"  [ERRO] {file_path.name}: {e}")

    # Esvaziar batch restante
    flush_batch()

    # Garantir sincronização e contagem do HNSW
    time.sleep(1)
    final_count = 0
    try:
        final_count = collection.count()
    except Exception as e:
        print(f"  [AVISO] Verificação de contagem: {e}")

    del collection
    del client
    gc.collect()

    print(f"\n{SEPARATOR}")
    print(f"  Indexação completa!")
    print(f"  {indexed_files} arquivos / {total_chunks} chunks indexados (Total na base: {final_count})")
    print(f"  Coleção: '{coll_name}' ({INDEX_DIR})")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    main()
