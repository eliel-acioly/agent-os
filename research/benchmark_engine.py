#!/usr/bin/env python3
"""
benchmark_engine.py — AntecipIA Aerospace-Grade Agent Platform v3.0
Motor de Benchmarks e Avaliação de Confiabilidade de Missão Crítica.
Testa latência do RAG, overhead do EDL, conformidade TypeScript e integridade dos agentes.
Uso: python .agents/research/benchmark_engine.py [--full] [--json]
"""

import sys
import time
import json
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse

AGENTS_DIR = Path(__file__).parent.parent
ROOT = AGENTS_DIR.parent
BENCHMARK_REPORT = AGENTS_DIR / "research" / "benchmark_report.json"

SEPARATOR = "═" * 70

# Metas de Padrão Aeroespacial (NASA / SpaceX Flight Software SLA)
SLA_TARGETS = {
    "edl_overhead_ms":       {"max": 5.0,    "unit": "ms", "desc": "Overhead do Head EDL por detecção"},
    "rag_query_latency_ms":  {"max": 2000.0, "unit": "ms", "desc": "Latência de busca vetorial RAG (ChromaDB CPU)"},
    "agent_skills_score":    {"min": 95.0,   "unit": "%",  "desc": "Score de completude dos SKILL.md"},
    "typescript_errors":     {"max": 0,      "unit": "err", "desc": "Erros de compilação estática TypeScript"},
}


def benchmark_edl() -> dict:
    """Mede a latência e estabilidade do EDL Uncertainty Provider."""
    try:
        sys.path.insert(0, str(ROOT / "services" / "antecipia-vision-worker" / "vllm_providers"))
        from edl_uncertainty_provider import EDLUncertaintyProvider, YOLODetection
        
        provider = EDLUncertaintyProvider(num_classes=80)
        
        # Warmup
        det = YOLODetection("person", 0, 0.90, [10, 10, 100, 200])
        for _ in range(10):
            provider.process_detection(det)

        # Medição de 100 iterações
        latencies = []
        for _ in range(100):
            t0 = time.perf_counter()
            res = provider.process_detection(det)
            latencies.append((time.perf_counter() - t0) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        p99_latency = sorted(latencies)[int(len(latencies) * 0.99)]

        passed = avg_latency <= SLA_TARGETS["edl_overhead_ms"]["max"]
        return {
            "name": "Evidential Deep Learning (EDL) Latency",
            "avg_ms": round(avg_latency, 3),
            "p99_ms": round(p99_latency, 3),
            "iterations": 100,
            "passed": passed,
            "target_max_ms": SLA_TARGETS["edl_overhead_ms"]["max"]
        }
    except Exception as e:
        return {"name": "EDL Latency", "passed": False, "error": str(e)}


def benchmark_rag() -> dict:
    """Mede a latência do motor de busca semântica RAG (ChromaDB)."""
    try:
        sys.path.insert(0, str(AGENTS_DIR / "rag"))
        from query_engine import query_rag

        # Warmup
        query_rag("YOLO detection", "AI_Edge", top_k=2)

        # Medição de 5 buscas representativas
        latencies = []
        queries = ["YOLO pipeline", "Socket.IO events", "Drizzle schema", "RLS security", "React UI"]
        for q in queries:
            t0 = time.perf_counter()
            res = query_rag(q, "Master", top_k=3)
            latencies.append((time.perf_counter() - t0) * 1000)

        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

        passed = avg_latency <= SLA_TARGETS["rag_query_latency_ms"]["max"]
        return {
            "name": "RAG ChromaDB Vector Search Latency",
            "avg_ms": round(avg_latency, 2),
            "p95_ms": round(p95_latency, 2),
            "queries_executed": len(latencies),
            "passed": passed,
            "target_max_ms": SLA_TARGETS["rag_query_latency_ms"]["max"]
        }
    except Exception as e:
        return {"name": "RAG Latency", "passed": False, "error": str(e)}


def benchmark_skills_audit() -> dict:
    """Avalia o score médio de qualidade dos SKILL.md de todos os agentes canônicos AntecipIA."""
    try:
        sys.path.insert(0, str(AGENTS_DIR / "self_improvement" / "scripts"))
        from audit_skills import score_skill, SKILLS_DIR
        
        # Filtra os 12 agentes canônicos do AntecipIA
        all_skills = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir() and d.name.startswith("antecipia-")])
        scores = []
        for sdir in all_skills:
            sfile = sdir / "SKILL.md"
            if sfile.exists():
                res = score_skill(sfile)
                scores.append(res["score"])

        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        passed = avg_score >= SLA_TARGETS["agent_skills_score"]["min"]

        return {
            "name": "Agent Skills Quality & Completeness",
            "avg_score": round(avg_score, 1),
            "min_score": min_score,
            "total_skills": len(scores),
            "passed": passed,
            "target_min_score": SLA_TARGETS["agent_skills_score"]["min"]
        }
    except Exception as e:
        return {"name": "Skills Audit", "passed": False, "error": str(e)}


def benchmark_typescript() -> dict:
    """Verifica compilação estática TypeScript."""
    try:
        cmd = ["npx", "tsc", "--noEmit"]
        result = subprocess.run(
            cmd, cwd=str(ROOT / "antecipia-ui"),
            capture_output=True, text=True, timeout=30, shell=True
        )
        passed = result.returncode == 0
        return {
            "name": "TypeScript Type Integrity Check (antecipia-ui)",
            "errors": 0 if passed else 1,
            "passed": passed,
            "output": result.stdout.strip() if not passed else "0 errors"
        }
    except Exception as e:
        return {"name": "TypeScript Check", "passed": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Motor de Benchmarks Aeroespaciais.")
    parser.add_argument("--json", "-j", action="store_true", help="Saída em formato JSON")
    args = parser.parse_args()

    print(f"\n{SEPARATOR}")
    print("  🚀 AntecipIA Benchmark Engine — NASA / SpaceX Reliability Standard")
    print(f"  Data de Execução: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEPARATOR)

    tests = [
        ("1/4. Incerteza EDL", benchmark_edl),
        ("2/4. Latência RAG", benchmark_rag),
        ("3/4. Score de Agentes", benchmark_skills_audit),
        ("4/4. TypeScript Check", benchmark_typescript),
    ]

    results = {}
    all_passed = True

    for label, test_fn in tests:
        print(f"\n  ⏳ Executando {label}...")
        res = test_fn()
        results[res.get("name", label)] = res
        status_icon = "✅ APROVADO" if res.get("passed") else "❌ FALHOU"
        print(f"     Status: {status_icon}")

        if not res.get("passed"):
            all_passed = False
            if "error" in res:
                print(f"     Erro: {res['error']}")
        else:
            for k, v in res.items():
                if k not in ["name", "passed"]:
                    print(f"     • {k}: {v}")

    print(f"\n{SEPARATOR}")
    if all_passed:
        print("  🏆 CERTIFICADO AEROESPACIAL: TODOS OS BENCHMARKS APROVADOS (100% SLA)")
        print("  A plataforma de agentes opera em padrão de missão crítica.")
    else:
        print("  ⚠️  FALHAS DETECTADAS NOS BENCHMARKS — Ação corretiva necessária.")
    print(SEPARATOR + "\n")

    # Salvar relatório
    BENCHMARK_REPORT.parent.mkdir(parents=True, exist_ok=True)
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "overall_passed": all_passed,
        "results": results
    }
    BENCHMARK_REPORT.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.json:
        print(json.dumps(report_data, indent=2, ensure_ascii=False))

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
