#!/usr/bin/env python3
"""
AGENT-OS — REPO MAP & CENTRALITY ENGINE (Inspirado no Aider & SWE-agent)
Gera um mapa semântico e topológico do repositório calculando a centralidade
(PageRank / In-Degree) dos arquivos e componentes para fornecer o contexto mais
relevante para as LLMs sem estourar o limite de tokens.
"""

import sys
import os
import re
import argparse
import json
from collections import defaultdict

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def build_repo_graph(target_dir, max_files=200):
    """Varre o repositório e extrai referências de import para construir o grafo"""
    graph = defaultdict(set)
    files_map = {}
    
    # Extensões suportadas
    valid_exts = ('.ts', '.tsx', '.js', '.jsx', '.py', '.go', '.rs')
    ignore_dirs = ('node_modules', 'dist', 'build', '.git', 'venv', '.venv', 'weights')

    scanned_count = 0
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if f.endswith(valid_exts):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, target_dir).replace('\\', '/')
                files_map[rel_path] = f
                scanned_count += 1
                if scanned_count >= max_files:
                    break

    # Analisa imports em cada arquivo
    for rel_path in files_map.keys():
        full_path = os.path.join(target_dir, rel_path)
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as fp:
                content = fp.read()
                # Extrai caminhos de import simples
                imports = re.findall(r'(?:from|import)\s+[\'"]([^\'"]+)[\'"]', content)
                for imp in imports:
                    target_name = os.path.basename(imp).split('.')[0]
                    # Procura se algum arquivo do repo tem esse nome
                    for cand_rel, cand_file in files_map.items():
                        if target_name in cand_file and cand_rel != rel_path:
                            graph[rel_path].add(cand_rel)
        except Exception:
            continue

    return graph, files_map

def compute_centrality(graph, files_map):
    """Calcula in-degree (quantos outros arquivos importam este)"""
    in_degree = defaultdict(int)
    for source, targets in graph.items():
        for target in targets:
            in_degree[target] += 1

    ranked = sorted(files_map.keys(), key=lambda f: in_degree[f], reverse=True)
    results = []
    for f in ranked[:15]:
        results.append({
            "file": f,
            "incoming_references": in_degree[f],
            "is_architectural_hub": in_degree[f] >= 3
        })
    return results

def main():
    parser = argparse.ArgumentParser(description="Agent-OS Repo Map & Centrality Engine")
    parser.add_argument("--dir", "-d", default=".", help="Diretório a ser mapeado")
    parser.add_argument("--top", "-t", type=int, default=10, help="Número de componentes mais centrais")
    parser.add_argument("--json", action="store_true", help="Saída em formato JSON")
    args = parser.parse_args()

    graph, files_map = build_repo_graph(args.dir)
    ranking = compute_centrality(graph, files_map)

    if args.json:
        print(json.dumps(ranking[:args.top], indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print(f"  AGENT-OS REPO MAP: ARQUITETURA & COMPONENTES CENTRAIS")
        print("=" * 70)
        print(f"Mapeados {len(files_map)} arquivos de código. Top {args.top} núcleos centrais:\n")
        for idx, item in enumerate(ranking[:args.top], 1):
            hub_badge = "🌟 [HUB CENTRAL]" if item["is_architectural_hub"] else "📄"
            print(f"  {idx:2d}. {hub_badge} {item['file']} ({item['incoming_references']} conexões)")
        print("=" * 70)

if __name__ == "__main__":
    main()
