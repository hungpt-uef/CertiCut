"""Compare a capacity-exact weighted K-way heuristic to CertiCut SCIP bounds."""

from __future__ import annotations

import json
from math import exp, isfinite
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.baselines.kway_greedy import solve_weighted_kway_greedy
from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    source = ROOT / "results" / "e9_k_symmetry_scaling.jsonl"
    bounds = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line]
    destination = ROOT / "results" / "e9_k_weighted_heuristic.jsonl"
    with destination.open("w", encoding="utf-8") as stream:
        for bound in bounds:
            family, n, k, seed = bound["family"], bound["num_qubits"], bound["K"], bound["seed"]
            graph = build_interaction_graph(make_heterogeneous_qpd_circuit(family, n, 20260812 + seed), cost_model="qiskit_qpd")
            partition, objective, runtime = solve_weighted_kway_greedy(graph, capacities=_capacities(n, k), seed=seed)
            lower = bound["lower_bound_log"]
            regret = exp(objective - lower) if lower is not None and isfinite(lower) else None
            row = {"family": family, "num_qubits": n, "K": k, "seed": seed, "heuristic": "weighted_kway_greedy_swap",
                   "runtime_s": runtime, "objective_log_cost": objective, "fragment_sizes": tuple(partition.count(fragment) for fragment in range(k)),
                   "certicut_lower_bound_log": lower, "certicut_regret_factor_upper_bound": regret, "certicut_status": bound["status"]}
            stream.write(json.dumps(row) + "\n")
            print(f"[{family} n={n} K={k} seed={seed}] regret<={regret}; t={runtime:.3f}s")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
