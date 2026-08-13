"""Run fair Track A/B baseline sanity artifacts, not cross-track performance claims."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.baselines.graph_heuristics import solve_graph_heuristic
from certicut.baselines.qiskit_cut_finder import find_gate_only_cuts
from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def main() -> None:
    circuit = make_six_qubit_toy_circuit()
    graph = build_interaction_graph(circuit)
    certicut = solve_certified_bnb(
        graph, qmax=3, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant="h2"
    )
    exact = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    summary = {
        "track_a_exact_balanced": {
            "certicut": certicut.as_dict(),
            "phase2_exact": exact.as_dict(),
            "h2": solve_graph_heuristic(graph, qmax=3, variant="h2").as_dict(),
            "h3": solve_graph_heuristic(graph, qmax=3, variant="h3").as_dict(),
        },
        "track_b_practical_qmax": {
            "qiskit_gate_only": find_gate_only_cuts(circuit, qmax=3).as_dict(),
        },
        "fairness_note": "Track A requires exact balanced K=2. Track B only requires Qmax and is not used for direct optimality ranking against Track A.",
    }
    Path("results/phase5_baseline_sanity.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
