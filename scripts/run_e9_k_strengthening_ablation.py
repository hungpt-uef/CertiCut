"""Ablate fixed-capacity cardinality, metric, and label symmetry cuts."""

from __future__ import annotations

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


CONFIGURATIONS = {
    "base": {"cross_pair_strengthening": False, "metric_strengthening": False, "symmetry_breaking": False},
    "symmetry_only": {"cross_pair_strengthening": False, "metric_strengthening": False, "symmetry_breaking": True},
    "cardinality_symmetry": {"cross_pair_strengthening": True, "metric_strengthening": False, "symmetry_breaking": True},
    "full_metric": {"cross_pair_strengthening": True, "metric_strengthening": True, "symmetry_breaking": True},
}


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    destination = ROOT / "results" / "e9_k_strengthening_ablation.jsonl"
    done = set()
    if destination.exists():
        done = {
            (row["family"], row["num_qubits"], row["K"], row["seed"], row["configuration"])
            for row in map(json.loads, destination.read_text(encoding="utf-8").splitlines()) if row
        }
    with destination.open("a", encoding="utf-8") as stream:
        for family in ("random_matching", "community_matching", "weighted_repeat"):
            for n in (20, 32):
                for k in (3, 4):
                    for seed in range(3):
                        circuit = make_heterogeneous_qpd_circuit(family, n, 20260812 + seed)
                        graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
                        capacity = _capacities(n, k)
                        for name, options in CONFIGURATIONS.items():
                            if (family, n, k, seed, name) in done:
                                continue
                            result = solve_scip_k_partition(
                                graph, num_fragments=k, lower_capacities=capacity, upper_capacities=capacity,
                                time_limit_s=5.0, **options,
                            )
                            row = {
                                "family": family, "num_qubits": n, "K": k, "seed": seed,
                                "configuration": name, "status": result.status, "runtime_s": result.runtime_s,
                                "nodes": result.nodes, "objective_log_cost": result.objective_log_cost,
                                "factor": result.certificate.overhead_factor_bound if result.certificate else None,
                            }
                            stream.write(json.dumps(row) + "\n")
                            print(f"[{name} {family} n={n} K={k} seed={seed}] {result.status}; F={row['factor']}; t={result.runtime_s:.2f}s")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
