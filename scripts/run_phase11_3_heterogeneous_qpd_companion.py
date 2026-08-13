"""Run a resumable heterogeneous-QPD companion corpus with exact plan regret."""

from __future__ import annotations

import hashlib
import json
from math import exp
from pathlib import Path
import sys

from qiskit import qasm3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph, graph_partition_objective, valid_two_fragment_partitions
from certicut.optimization.bnb import solve_certified_bnb


FAMILIES = ("random_matching", "ring_even_odd", "community_matching", "dense_shuffled", "weighted_repeat")
SIZES = (12, 14, 16)
SEEDS = range(8)
DEADLINE_S = 30.0
COUNT_OVERHEADS = {"cx": exp(1), "cz": exp(1), "iswap": exp(1), "rzz": exp(1)}


def _canonical_plan(graph, qmax: int) -> tuple[tuple[int, ...], float]:
    best_partition = None
    best_value = float("inf")
    for partition in valid_two_fragment_partitions(graph.num_qubits, qmax):
        value = graph_partition_objective(graph, partition)
        if value < best_value - 1e-12:
            best_partition, best_value = partition, value
    assert best_partition is not None
    return best_partition, best_value


def _record(family: str, num_qubits: int, seed: int) -> dict[str, object]:
    circuit = make_heterogeneous_qpd_circuit(family, num_qubits, seed)
    qmax = num_qubits // 2
    count_graph = build_interaction_graph(circuit, cost_model="legacy_cx", qpd_overheads=COUNT_OVERHEADS)
    qpd_graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    count_partition, count_value = _canonical_plan(count_graph, qmax)
    qpd_partition, qpd_value = _canonical_plan(qpd_graph, qmax)
    qpd_at_count = graph_partition_objective(qpd_graph, count_partition)
    result = solve_certified_bnb(
        qpd_graph, qmax=qmax, exact_num_fragments=True, time_limit_s=DEADLINE_S,
        lp_variant="b2s_root", warm_start_variant="h2", collect_profile=True,
    )
    certificate = result.certificate
    palette_counts: dict[str, int] = {}
    for edge in qpd_graph.edges:
        for gate in edge.gates:
            label = gate.gate_type if not gate.gate_params else f"{gate.gate_type}({gate.gate_params[0]:.12g})"
            palette_counts[label] = palette_counts.get(label, 0) + 1
    fingerprint = hashlib.sha256(qasm3.dumps(circuit).encode("utf-8")).hexdigest()
    return {
        "experiment": "E5_heterogeneous_qpd_nonzero_companion",
        "family": family,
        "num_qubits": num_qubits,
        "seed": seed,
        "requested_deadline_s": DEADLINE_S,
        "cost_model": "qiskit_qpd_0.10.0_independent",
        "circuit_fingerprint_sha256": fingerprint,
        "palette_counts": dict(sorted(palette_counts.items())),
        "count_partition": count_partition,
        "count_at_count_plan": count_value,
        "qpd_log_at_count_plan": qpd_at_count,
        "qpd_partition": qpd_partition,
        "qpd_log_at_qpd_plan": qpd_value,
        "regret_log": qpd_at_count - qpd_value,
        "regret_factor": exp(qpd_at_count - qpd_value),
        "count_delta": graph_partition_objective(count_graph, qpd_partition) - count_value,
        "partitions_differ": count_partition != qpd_partition,
        "status": result.status,
        "expanded_nodes": result.expanded_nodes,
        "lower_bound_log": certificate.lower_bound_log,
        "upper_bound_log": certificate.upper_bound_log,
        "gap_log": certificate.additive_log_gap,
        "factor_bound": certificate.overhead_factor_bound,
        "timeline": [event.__dict__ for event in result.timeline],
    }


def main() -> None:
    output = Path("results/phase11_3_heterogeneous_qpd_nonzero_companion.jsonl")
    completed = set()
    if output.exists():
        completed = {(row["family"], row["num_qubits"], row["seed"]) for row in map(json.loads, output.read_text(encoding="utf-8").splitlines())}
    with output.open("a", encoding="utf-8") as stream:
        for family in FAMILIES:
            for num_qubits in SIZES:
                for seed in SEEDS:
                    key = (family, num_qubits, seed)
                    if key not in completed:
                        stream.write(json.dumps(_record(*key)) + "\n")
                        stream.flush()


if __name__ == "__main__":
    main()
