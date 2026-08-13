"""Evaluate KaHIP K-way incumbents against CertiCut solver bound reports."""

from __future__ import annotations

import json
from math import exp, isfinite
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.baselines.kahip import solve_kahip_k
from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    source = ROOT / "results" / "e7_k_heterogeneous_scaling_replicated.jsonl"
    bounds = {(row["family"], row["num_qubits"], row["K"], row["seed"]): row for row in map(json.loads, source.read_text(encoding="utf-8").splitlines()) if row}
    destination = ROOT / "results" / "e9_k_kahip_baseline.jsonl"
    with destination.open("w", encoding="utf-8") as stream:
        for family, n, k, seed in sorted(bounds):
            bound = bounds[family, n, k, seed]
            graph = build_interaction_graph(make_heterogeneous_qpd_circuit(family, n, 20260812 + seed), cost_model="qiskit_qpd")
            result = solve_kahip_k(graph, num_fragments=k, capacities=_capacities(n, k), seed=seed)
            lower = bound["lower_bound_log"]
            regret = exp(result.objective_log_cost - lower) if result.objective_log_cost is not None and lower is not None and isfinite(lower) else None
            row = {"family": family, "num_qubits": n, "K": k, "seed": seed, "status": result.status,
                   "runtime_s": result.runtime_s, "qpd_log_cost": result.objective_log_cost,
                   "certicut_lower_bound_log": lower, "certicut_regret_factor_upper_bound": regret,
                   "certicut_status": bound["status"]}
            stream.write(json.dumps(row) + "\n")
            print(f"[{family} n={n} K={k} seed={seed}] {result.status}; regret<={regret}")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
