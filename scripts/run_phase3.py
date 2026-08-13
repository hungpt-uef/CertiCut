"""Run certified anytime B&B on the handbook toy circuit."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb


def main() -> None:
    result = solve_certified_bnb(
        build_interaction_graph(make_six_qubit_toy_circuit()), qmax=3, exact_num_fragments=True
    )
    summary = result.as_dict()
    Path("results/phase3_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with Path("results/phase3_timeline.jsonl").open("w", encoding="utf-8") as timeline:
        for event in result.timeline:
            timeline.write(json.dumps(event.__dict__) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
