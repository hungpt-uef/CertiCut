"""Summarize the frozen heterogeneous-QPD companion corpus."""

from __future__ import annotations

import json
from math import exp
from pathlib import Path
from statistics import median
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph, graph_partition_objective, valid_two_fragment_partitions


COUNT_OVERHEADS = {"cx": exp(1), "cz": exp(1), "iswap": exp(1), "rzz": exp(1)}


def _percentile(values: list[float], fraction: float) -> float:
    return sorted(values)[int(fraction * (len(values) - 1))]


def _regret_record(row: dict[str, object]) -> dict[str, object]:
    circuit = make_heterogeneous_qpd_circuit(row["family"], row["num_qubits"], row["seed"])
    count_graph = build_interaction_graph(circuit, cost_model="legacy_cx", qpd_overheads=COUNT_OVERHEADS)
    qpd_graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    values = [
        (partition, graph_partition_objective(count_graph, partition), graph_partition_objective(qpd_graph, partition))
        for partition in valid_two_fragment_partitions(row["num_qubits"], row["num_qubits"] // 2)
    ]
    min_count = min(count for _, count, _ in values)
    count_optima = [value for value in values if abs(value[1] - min_count) <= 1e-9]
    count_partition, _, qpd_at_any_count_optimum = min(count_optima, key=lambda value: (value[2], value[0]))
    qpd_optimum = min(qpd for _, _, qpd in values)
    qpd_optima = [value for value in values if abs(value[2] - qpd_optimum) <= 1e-9]
    qpd_partition, min_count_at_qpd_optimum, _ = min(qpd_optima, key=lambda value: (value[1], value[0]))
    count_crossed = _crossed_gate_counts(qpd_graph, count_partition)
    qpd_crossed = _crossed_gate_counts(qpd_graph, qpd_partition)
    gate_delta = {
        gate: qpd_crossed.get(gate, 0) - count_crossed.get(gate, 0)
        for gate in sorted(set(count_crossed) | set(qpd_crossed))
    }
    return {
        "family": row["family"],
        "regret_log": qpd_at_any_count_optimum - qpd_optimum,
        "regret_factor": exp(qpd_at_any_count_optimum - qpd_optimum),
        "count_delta": min_count_at_qpd_optimum - min_count,
        "gate_delta": gate_delta,
    }


def _crossed_gate_counts(graph, partition: tuple[int, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for edge in graph.edges:
        if partition[edge.u] != partition[edge.v]:
            for gate in edge.gates:
                label = gate.gate_type if not gate.gate_params else f"{gate.gate_type}({gate.gate_params[0]:.12g})"
                counts[label] = counts.get(label, 0) + 1
    return counts


def main() -> None:
    rows = [json.loads(line) for line in Path("results/phase11_3_heterogeneous_qpd_nonzero_companion.jsonl").read_text(encoding="utf-8").splitlines()]
    robust = [_regret_record(row) for row in rows]
    factors = [record["regret_factor"] for record in robust]
    strict = [record for record in robust if record["regret_log"] > 1e-9]
    by_family = {}
    for family in sorted({row["family"] for row in rows}):
        subset = [record for record in robust if record["family"] == family]
        subset_factors = [record["regret_factor"] for record in subset]
        by_family[family] = {
            "records": len(subset),
            "strict_reversals": sum(record["regret_log"] > 1e-9 for record in subset),
            "median_factor": median(subset_factors),
            "p90_factor": _percentile(subset_factors, 0.9),
        }
    summary = {
        "experiment": "E5_heterogeneous_qpd_nonzero_companion",
        "records": len(rows),
        "target_records": 120,
        "cost_model": "qiskit_qpd_0.10.0_independent",
        "status_counts": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})},
        "strict_reversals": len(strict),
        "strict_reversal_fraction": len(strict) / len(rows),
        "count_optimum_qpd_regret_definition": "min_{P: count(P)=count*} J(P) - min_P J(P)",
        "regret_factor": {"median": median(factors), "p90": _percentile(factors, 0.9), "maximum": max(factors)},
        "strict_regret_factor": {
            "median": median([record["regret_factor"] for record in strict]),
            "p90": _percentile([record["regret_factor"] for record in strict], 0.9),
            "maximum": max(record["regret_factor"] for record in strict),
        },
        "count_delta": {
            "positive": sum(record["count_delta"] > 1e-9 for record in strict),
            "zero": sum(abs(record["count_delta"]) <= 1e-9 for record in strict),
            "median": median(record["count_delta"] for record in strict),
            "maximum": max(record["count_delta"] for record in strict),
        },
        "gate_delta_totals": {
            gate: sum(record["gate_delta"].get(gate, 0) for record in strict)
            for gate in sorted({gate for record in strict for gate in record["gate_delta"]})
        },
        "root_closed": sum(row["timeline"][0]["additive_log_gap"] <= 1e-9 for row in rows),
        "by_family": by_family,
    }
    Path("results/phase11_3_heterogeneous_qpd_nonzero_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
