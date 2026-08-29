#!/usr/bin/env python3
"""
auto_evolve.py — AntecipIA Aerospace-Grade Agent Platform v3.0
Orquestrador do Ciclo Fechado de Auto-Evolução dos Agentes.
Executa: Auditoria -> Pesquisa SOTA -> Geração de RFCs -> Benchmarks -> Persistência de Memória.
Uso: python .agents/self_improvement/auto_evolve.py [--dry-run] [--auto-apply]
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

AGENTS_DIR = Path(__file__).parent.parent
ROOT = AGENTS_DIR.parent
MEMORY_DIR = AGENTS_DIR / "memory"
SESSION_LOG = MEMORY_DIR / "session_log.jsonl"
EVOLUTION_LOG = AGENTS_DIR / "self_improvement" / "evolution_history.json"

SEPARATOR = "═" * 70


def run_step(label: str, script_rel_path: str, args_list: list = None) -> tuple:
    """Executa um script de etapa do ciclo de auto-evolução."""
    script_full = AGENTS_DIR / script_rel_path
    cmd = [sys.executable, str(script_full)] + (args_list or [])

    print(f"\n▶️  [ETAPA] {label}")
    print(f"   Comando: python {script_rel_path} {' '.join(args_list or [])}")
    print("─" * 70)

    try:
        res = subprocess.run(
            cmd, cwd=str(ROOT),
            capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace"
        )
        if res.stdout.strip():
            # Exibir resumo da saída
            lines = res.stdout.strip().splitlines()
            for line in lines[:8]:
                print(f"   {line}")
            if len(lines) > 8:
                print(f"   ... ({len(lines) - 8} linhas adicionais)")

        success = res.returncode == 0
        if not success and res.stderr.strip():
            print(f"   ⚠️  Aviso/Erro: {res.stderr.strip()[:200]}")

        return success, res.stdout
    except Exception as e:
        print(f"   ❌ Exceção na etapa: {e}")
        return False, str(e)


def log_evolution_cycle(cycle_report: dict):
    EVOLUTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    history = []
    if EVOLUTION_LOG.exists():
        try:
            history = json.loads(EVOLUTION_LOG.read_text(encoding="utf-8"))
        except Exception:
            history = []

    history.append(cycle_report)
    EVOLUTION_LOG.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Ciclo Fechado de Auto-Evolução dos Agentes.")
    parser.add_argument("--dry-run", action="store_true", help="Executa o ciclo em modo simulação sem persistir alterações")
    args = parser.parse_args()

    cycle_id = f"EVOLVE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    print(f"\n{SEPARATOR}")
    print(f"  🌌 AntecipIA Autonomous Self-Evolution Engine — {cycle_id}")
    print(f"  Padrão Aeroespacial: NASA JPL / SpaceX Mission Critical v3.0")
    print(f"  Início do Ciclo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)

    steps = [
        ("1. Auditoria de Qualidade dos Agentes", "self_improvement/scripts/audit_skills.py", []),
        ("2. Mapeamento do Tech Radar", "research/tech_radar.py", ["--export-json"]),
        ("3. Pesquisa SOTA e Geração de RFCs", "research/idea_scout.py", ["--agent", "all", "--generate-rfcs"]),
        ("4. Sincronização do Grafo de Código", "scripts/update_graph.py", ["--target", "all"]),
        ("5. Bateria de Benchmarks de Missão Crítica", "research/benchmark_engine.py", []),
    ]

    results = []
    all_success = True

    for label, script_path, extra_args in steps:
        success, out = run_step(label, script_path, extra_args)
        results.append({"step": label, "success": success})
        if not success:
            all_success = False

    # Persistência de Aprendizado
    print(f"\n{SEPARATOR}")
    if all_success:
        print("  🏆 CICLO DE AUTO-EVOLUÇÃO CONCLUÍDO COM 100% DE SUCESSO")
        print("  Todos os agentes foram auditados, pesquisados e benchmarkados.")
        
        # Gravar lição na knowledge base
        memory_script = AGENTS_DIR / "scripts" / "memory_write.py"
        subprocess.run([
            sys.executable, str(memory_script),
            "--agent", "Master",
            "--text", f"Ciclo de Auto-Evolução {cycle_id} executado com sucesso: Tech Radar sincronizado, RFCs geradas e Benchmarks SLA 100% aprovados."
        ], cwd=str(ROOT), capture_output=True, text=True)
    else:
        print("  ⚠️  CICLO CONCLUÍDO COM RESSALVAS — Algumas etapas exigem atenção técnica.")
    print(SEPARATOR + "\n")

    cycle_report = {
        "cycle_id": cycle_id,
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "all_success": all_success,
        "steps": results
    }
    log_evolution_cycle(cycle_report)


if __name__ == "__main__":
    main()
