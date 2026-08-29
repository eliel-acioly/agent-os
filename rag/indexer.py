#!/usr/bin/env python3
"""
indexer.py — AntecipIA Agent Platform v2.0 — RAG Layer
Indexa o codebase do projeto em um vector store ChromaDB persistente.
Uso: python .agents/rag/indexer.py [--target all|antecipia-api|antecipia-ui|services]
"""

import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = Path(__file__).parent.parent
RAG_DIR = AGENTS_DIR / "rag"
INDEX_DIR = RAG_DIR / "knowledge" / "project_index"

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

# Diretórios de código por alvo
TARGET_DIRS = {
    "antecipia-api": [ROOT / "antecipia-api" / "src", ROOT / "antecipia-api" / "server"],
    "antecipia-ui":  [ROOT / "antecipia-ui" / "src"],
    "services":      [ROOT / "services"],
    "agents":        [AGENTS_DIR / "skills"],
    "shared":        [ROOT / "shared"],
    "all": [
        ROOT / "antecipia-api" / "src",
        ROOT / "antecipia-api" / "server",
        ROOT / "antecipia-ui" / "src",
        ROOT / "services",
        ROOT / "shared",
        AGENTS_DIR / "skills",
    ]
}


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
    parser = argparse.ArgumentParser(description="Indexa o codebase AntecipIA no RAG ChromaDB.")
    parser.add_argument("--target", "-t",
                        choices=list(TARGET_DIRS.keys()),
                        default="all", help="Alvo de indexação")
    parser.add_argument("--reset", "-r", action="store_true",
                        help="Reinicia a coleção antes de indexar (re-indexação completa)")
    args = parser.parse_args()

    print(f"\n{SEPARATOR}")
    print(f"  🗂️  AntecipIA RAG Indexer — ChromaDB")
    print(f"  Target: {args.target.upper()}")
    print(f"  Index: {INDEX_DIR}")
    print(SEPARATOR)

    client = get_chroma_client()
    collection_name = f"antecipia_{args.target}"

    if args.reset:
        try:
            client.delete_collection(collection_name)
            print(f"[INFO] Coleção '{collection_name}' removida para re-indexação.")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": f"AntecipIA codebase — {args.target}", "hnsw:space": "cosine"}
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

    # Indexar em batches
    BATCH_SIZE = 50
    total_chunks = 0
    indexed_files = 0

    for i, file_path in enumerate(all_files):
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content.strip()) < 20:
                continue

            rel_path = str(file_path.relative_to(ROOT))
            chunks = chunk_code(content, rel_path)

            if not chunks:
                continue

            # Preparar batch para ChromaDB
            ids = []
            documents = []
            metadatas = []

            for j, chunk in enumerate(chunks):
                chunk_id = hashlib.md5(f"{rel_path}:{j}:{chunk['text'][:50]}".encode()).hexdigest()
                ids.append(chunk_id)
                documents.append(chunk["text"])
                metadatas.append({
                    "source": chunk["source"],
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "file_type": INDEXED_EXTENSIONS.get(file_path.suffix, "Unknown"),
                    "indexed_at": datetime.now().isoformat()
                })

            # Upsert para evitar duplicatas
            collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            total_chunks += len(chunks)
            indexed_files += 1

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(all_files)}] {indexed_files} arquivos, {total_chunks} chunks indexados...")

        except Exception as e:
            print(f"  [ERRO] {file_path.name}: {e}")

    print(f"\n{SEPARATOR}")
    print(f"  ✅ Indexação completa!")
    print(f"  📊 {indexed_files} arquivos / {total_chunks} chunks indexados")
    print(f"  💾 Coleção: '{collection_name}' ({INDEX_DIR})")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    main()
