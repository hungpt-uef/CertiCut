"""Solve the Phase 0 toy with the exact Phase 2 MILP."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import brute_force_exact_partition, solve_exact_partition


def main() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    solution = solve_exact_partition(
        graph, num_fragments=2, qmax=3, exact_num_fragments=True
    )
    ground_truth = brute_force_exact_partition(
        graph, num_fragments=2, qmax=3, exact_num_fragments=True
    )
    summary = {
        **solution.as_dict(),
        "bruteforce_objective_log_cost": ground_truth.objective_log_cost,
        "matches_ground_truth": solution.objective_log_cost == ground_truth.objective_log_cost,
    }
    output = Path("results/phase2_exact_summary.json")
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
