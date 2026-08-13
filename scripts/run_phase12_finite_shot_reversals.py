"""Frozen E8 finite-shot equal-budget audit for E5 witnesses and control."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition
from certicut.qiskit_bridge.operational import validate_finite_shot_comparison


CASES = (
    # Fixed before full execution: moderate reversal, strong reversal, no-reversal control.
    ("moderate_reversal", "dense_shuffled", 12, 2),
    ("strong_reversal", "community_matching", 12, 3),
    ("no_reversal_control", "ring_even_odd", 12, 0),
)
OBSERVABLES = ("Z" * 12, "X" + "I" * 11)

def _solution(graph, partition):
    base = solve_exact_partition(graph, num_fragments=2, qmax=graph.num_qubits // 2, exact_num_fragments=True)
    cuts = tuple((edge.u, edge.v) for edge in graph.edges if partition[edge.u] != partition[edge.v])
    instructions = tuple(index for edge in graph.edges if partition[edge.u] != partition[edge.v] for index in edge.instruction_indices)
    objective = sum(edge.qpd_log_cost for edge in graph.edges if partition[edge.u] != partition[edge.v])
    return replace(base, partition=tuple(partition), fragments=tuple(tuple(q for q, label in enumerate(partition) if label == side) for side in (0, 1)), cut_edges=cuts, cut_instruction_indices=instructions, objective_log_cost=objective)


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/phase11_3_heterogeneous_qpd_nonzero_companion.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("results/phase12_e8_finite_shot.jsonl"))
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--qpd-samples", type=int, default=16)
    parser.add_argument("--trials", type=int, default=50)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    indexed = {(row["family"], row["num_qubits"], row["seed"]): row for row in rows}
    completed = set()
    if args.output.exists():
        completed = {json.loads(line)["case_id"] for line in args.output.read_text(encoding="utf-8").splitlines()}
    with args.output.open("a", encoding="utf-8") as stream:
        for case_id, family, num_qubits, seed in CASES:
            if case_id in completed:
                continue
            row = indexed[(family, num_qubits, seed)]
            if case_id == "no_reversal_control" and row["regret_log"] > 1e-10:
                raise AssertionError("negative control unexpectedly has a reversal")
            if case_id != "no_reversal_control" and row["regret_log"] <= 1e-10:
                raise AssertionError("reversal case unexpectedly has no reversal")
            circuit = make_heterogeneous_qpd_circuit(row["family"], row["num_qubits"], row["seed"])
            graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
            comparison = validate_finite_shot_comparison(
                circuit, graph, (_solution(graph, row["count_partition"]), _solution(graph, row["qpd_partition"])),
                total_shots_per_seed=args.shots, qpd_samples_per_seed=args.qpd_samples,
                seeds=tuple(range(args.trials)), observables=OBSERVABLES,
            )
            stream.write(json.dumps({
                "experiment": "E8_finite_shot_equal_budget_reversal",
                "case_id": case_id,
                "witness": {key: row[key] for key in ("family", "num_qubits", "seed", "regret_factor", "regret_log", "partitions_differ")},
                "comparison": comparison.as_dict(),
            }) + "\n")
            stream.flush()


if __name__ == "__main__":
    main()
