"""Heterogeneous-QPD capacitated K-way SCIP scalability matrix."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.k_partition import solve_scip_k_partition


FAMILIES = ("random_matching", "community_matching", "weighted_repeat")


def capacities(n: int, k: int) -> tuple[int, ...]:
    """Exact near-balanced capacities; each declared fragment is used."""
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", nargs="+", type=int, default=(20, 32, 40, 60))
    parser.add_argument("--fragments", nargs="+", type=int, default=(2, 3, 4, 5))
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--time-limit-s", type=float, default=10.0)
    parser.add_argument("--no-symmetry-breaking", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/e7_k_heterogeneous_scaling.jsonl"))
    args = parser.parse_args()
    if args.seeds < 1 or args.time_limit_s < 0:
        raise ValueError("seeds must be positive and time limit nonnegative")
    done = set()
    if args.output.exists():
        done = {(row["family"], row["num_qubits"], row["K"], row["seed"]) for row in map(json.loads, args.output.read_text(encoding="utf-8").splitlines())}
    with args.output.open("a", encoding="utf-8") as stream:
        for family in FAMILIES:
            for n in args.sizes:
                for k in args.fragments:
                    if not 1 < k <= n:
                        continue
                    for seed in range(args.seeds):
                        key = family, n, k, seed
                        if key in done:
                            continue
                        circuit = make_heterogeneous_qpd_circuit(family, n, 20260812 + seed)
                        graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
                        capacity = capacities(n, k)
                        result = solve_scip_k_partition(
                            graph, num_fragments=k, lower_capacities=capacity, upper_capacities=capacity,
                            time_limit_s=args.time_limit_s, symmetry_breaking=not args.no_symmetry_breaking,
                        )
                        certificate = result.certificate
                        record = {
                            "experiment": "E7_K_heterogeneous_qpd_scaling",
                            "family": family,
                            "num_qubits": n,
                            "K": k,
                            "capacities": capacity,
                            "seed": seed,
                            "cost_model": "qiskit_qpd_0.10.0_independent",
                            "time_limit_s": args.time_limit_s,
                            "status": result.status,
                            "runtime_s": result.runtime_s,
                            "nodes": result.nodes,
                            "lp_iterations": result.lp_iterations,
                            "objective_log_cost": result.objective_log_cost,
                            "gamma": result.gamma,
                            "lower_bound_log": certificate.lower_bound_log if certificate else None,
                            "upper_bound_log": certificate.upper_bound_log if certificate else None,
                            "factor": certificate.overhead_factor_bound if certificate else None,
                            "certificate_kind": certificate.certificate_kind if certificate else None,
                            "bound_status": result.bound_status,
                            "symmetry_breaking": not args.no_symmetry_breaking,
                        }
                        stream.write(json.dumps(record) + "\n")
                        stream.flush()
                        print(f"[{family} n={n} K={k}] {result.status}; F={record['factor']}; t={result.runtime_s:.3f}s")


if __name__ == "__main__":
    main()
