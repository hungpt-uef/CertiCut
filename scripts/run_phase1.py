"""Build and serialize deterministic Phase 1 interaction-graph results."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import (
    build_interaction_graph,
    gate_level_partition_objective,
    graph_partition_objective,
    valid_two_fragment_partitions,
)


def main() -> None:
    circuit = make_six_qubit_toy_circuit()
    graph = build_interaction_graph(circuit)
    partitions = tuple(valid_two_fragment_partitions(circuit.num_qubits, qmax=3))
    equivalent = all(
        graph_partition_objective(graph, partition)
        == gate_level_partition_objective(circuit, partition)
        for partition in partitions
    )
    summary = {
        "graph": graph.as_dict(),
        "objective_equivalence": {
            "qmax": 3,
            "valid_partition_count": len(partitions),
            "all_partitions_match": equivalent,
        },
    }
    output = Path("results/phase1_graph_summary.json")
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
