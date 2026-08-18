"""Resumable matched-objective E6/E9/E10 baseline suite."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys
from typing import Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.baselines.common import BaselineResult, safe_overhead
try:
    from certicut.baselines.kahip import solve_kahip_k
except ModuleNotFoundError:  # optional external multilevel partitioner
    solve_kahip_k = None
from certicut.baselines.kway_greedy import solve_weighted_kway_greedy
from certicut.baselines.kway_kl import solve_kway_kl
from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.circuits.ingestion import ingest_mqt_benchmark
from certicut.evaluation.baseline_metrics import matched_baseline_record, summarize_matched_records
from certicut.evaluation.canonical import evaluate_independent_qpd
from certicut.graph.interaction import build_interaction_graph
try:  # MQT-derived corpora (E6/E10) only; E9 is synthetic and needs no MQT import
    from scripts.run_phase11_3_real_heterogeneous_audit import FACTORIES, expose_semantic_two_qubit_ops
except ModuleNotFoundError:
    FACTORIES = None
    expose_semantic_two_qubit_ops = None


METHODS = ("Greedy-Swap", "KL-count", "KL-QPD", "KaHIP-QPD+repair")
DEFAULT_OUTPUT = ROOT / "results" / "upgrade_2026" / "e16_baseline_suite"


def _safe_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def _greedy(graph, capacities, seed, time_limit_s) -> BaselineResult:
    partition, _, runtime = solve_weighted_kway_greedy(
        graph, capacities=capacities, seed=seed, restarts=100_000, time_limit_s=time_limit_s,
    )
    evaluation = evaluate_independent_qpd(graph, partition, capacities)
    return BaselineResult(
        "Greedy-Swap", "K_exact_capacitated", "feasible", runtime,
        evaluation.objective_log_cost, safe_overhead(evaluation.objective_log_cost),
        evaluation.cut_instruction_indices, evaluation.fragment_sizes, None,
        "Capacity-exact multistart best-improving QPD swap baseline.", evaluation.partition,
    )


def _solvers(time_limit_s: float) -> dict[str, Callable[..., BaselineResult]]:
    return {
        "Greedy-Swap": lambda graph, capacities, seed: _greedy(graph, capacities, seed, time_limit_s),
        "KL-count": lambda graph, capacities, seed: solve_kway_kl(
            graph, capacities=capacities, weight_mode="count", seed=seed, restarts=100_000, time_limit_s=time_limit_s,
        ),
        "KL-QPD": lambda graph, capacities, seed: solve_kway_kl(
            graph, capacities=capacities, weight_mode="qpd", seed=seed, restarts=100_000, time_limit_s=time_limit_s,
        ),
        "KaHIP-QPD+repair": lambda graph, capacities, seed: solve_kahip_k(
            graph, num_fragments=len(capacities), capacities=capacities, seed=seed, mode="fast",
            refinement_time_limit_s=time_limit_s,
        ),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line] if path.exists() else []


def _append(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
        stream.flush()


def _e6_instances() -> Iterable[dict]:
    audit = json.loads((ROOT / "results" / "phase11_3_algorithm_heterogeneous_audit.json").read_text(encoding="utf-8"))
    for source in audit["records"]:
        if not source.get("eligible"):
            raise RuntimeError(f"E6 source became ineligible: {source['family']} n={source['n']}")
        yield {
            "corpus": "E6", "family": source["family"], "num_qubits": source["n"], "K": 2, "seed": 0,
            "capacities": (source["n"] // 2, source["n"] // 2),
            "lower_bound_log": source["J_qpd_optimum"], "solver_closed": True,
            "input_sha256": source["circuit_fingerprint_sha256"],
            "build": lambda s=source: build_interaction_graph(
                expose_semantic_two_qubit_ops(FACTORIES[s["family"]](s["n"])), cost_model="qiskit_qpd",
            ),
        }


def _e9_instances() -> Iterable[dict]:
    for source in _read_jsonl(ROOT / "results" / "e9_k_symmetry_scaling.jsonl"):
        family, n, k, seed = source["family"], source["num_qubits"], source["K"], source["seed"]
        circuit = make_heterogeneous_qpd_circuit(family, n, 20260812 + seed)
        yield {
            "corpus": "E9", "family": family, "num_qubits": n, "K": k, "seed": seed,
            "capacities": tuple(source["capacities"]), "lower_bound_log": source.get("lower_bound_log"),
            "solver_closed": source["status"] == "optimal", "input_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
            "build": lambda circuit=circuit: build_interaction_graph(circuit, cost_model="qiskit_qpd"),
        }


def _e10_instances() -> Iterable[dict]:
    for source in _read_jsonl(ROOT / "results" / "e10_algorithmic_kway.jsonl"):
        if source.get("status") == "ingestion_failed":
            continue
        family, n, k = source["family"], source["num_qubits"], source["K"]
        yield {
            "corpus": "E10", "family": family, "num_qubits": n, "K": k, "seed": 0,
            "capacities": tuple(source["capacities"]),
            "lower_bound_log": source.get("objective_log_cost") if source["status"] == "optimal" else None,
            "solver_closed": source["status"] == "optimal", "input_sha256": source["audit_fingerprint"],
            "build": lambda family=family, n=n: build_interaction_graph(
                ingest_mqt_benchmark(family, n, representation="native_qpd")[0], cost_model="qiskit_qpd",
            ),
        }


def _run(corpus: str, instances: Iterable[dict], *, output_dir: Path, time_limit_s: float, methods: tuple[str, ...], max_instances: int | None) -> list[dict]:
    destination = output_dir / f"{corpus.lower()}.jsonl"
    existing = _read_jsonl(destination)
    completed = {
        (row["family"], row["num_qubits"], row["K"], row["seed"], row.get("runner_method", row["method"]))
        for row in existing
    }
    solvers = _solvers(time_limit_s)
    attempted = 0
    for instance in instances:
        if max_instances is not None and attempted >= max_instances:
            break
        graph = instance["build"]()
        for method in methods:
            key = (instance["family"], instance["num_qubits"], instance["K"], instance["seed"], method)
            if key in completed:
                continue
            result = solvers[method](graph, instance["capacities"], instance["seed"])
            row = {
                "corpus": corpus, "family": instance["family"], "num_qubits": instance["num_qubits"],
                "K": instance["K"], "seed": instance["seed"], "capacities": instance["capacities"],
                "input_sha256": instance["input_sha256"], "runner_method": method,
                **matched_baseline_record(
                    result, lower_bound_log=instance["lower_bound_log"], solver_closed=instance["solver_closed"],
                ),
            }
            _append(destination, row)
            existing.append(row)
            print(f"{corpus} {instance['family']} n={instance['num_qubits']} K={instance['K']} {method}: {result.runtime_s:.3f}s", flush=True)
        attempted += 1
    return existing


def _write_manifest(output_dir: Path, corpora: tuple[str, ...], time_limit_s: float, methods: tuple[str, ...]) -> None:
    files = {corpus: output_dir / f"{corpus.lower()}.jsonl" for corpus in corpora}
    manifest = {
        "experiment": "E16 matched-objective baseline suite", "corpora": corpora, "methods": methods,
        "matched_objective": "fixed independent gate-QPD capacitated K-way partitioning",
        "python": sys.version, "platform": platform.platform(),
        "versions": {name: _safe_version(name) for name in ("qiskit", "qiskit-addon-cutting", "kahip", "mqt.bench", "pyscipopt")},
        "time_limit_s": time_limit_s,
        "kahip_protocol": "KaHIP FAST has no native binding time limit; reported runtime includes native call, exact repair, and budgeted refinement. It is not wall-clock budget matched.",
        "inputs": {
            "E6": _sha256(ROOT / "results" / "phase11_3_algorithm_heterogeneous_audit.json"),
            "E9": _sha256(ROOT / "results" / "e9_k_symmetry_scaling.jsonl"),
            "E10": _sha256(ROOT / "results" / "e10_algorithmic_kway.jsonl"),
        },
        "outputs": {corpus: {"records": len(_read_jsonl(path)), "sha256": _sha256(path)} for corpus, path in files.items() if path.exists()},
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", choices=("e6", "e9", "e10", "all"), default="all")
    parser.add_argument("--time-limit-s", type=float, default=0.1)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--max-instances", type=int)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.time_limit_s <= 0 or args.max_instances is not None and args.max_instances < 1:
        parser.error("time limit and max instances must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    requested = ("E6", "E9", "E10") if args.corpus == "all" else (args.corpus.upper(),)
    builders = {"E6": _e6_instances, "E9": _e9_instances, "E10": _e10_instances}
    all_records = []
    for corpus in requested:
        all_records.extend(_run(corpus, builders[corpus](), output_dir=args.output_dir, time_limit_s=args.time_limit_s, methods=tuple(args.methods), max_instances=args.max_instances))
    _write_manifest(args.output_dir, requested, args.time_limit_s, tuple(args.methods))
    summary = {corpus: summarize_matched_records([row for row in all_records if row["corpus"] == corpus]) for corpus in requested}
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
