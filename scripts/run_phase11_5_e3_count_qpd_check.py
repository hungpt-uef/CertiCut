"""Exact count-versus-QPD check on small native MQT Bench circuits."""

from __future__ import annotations

import json
from math import exp
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.ingestion import ingest_mqt_benchmark
from certicut.graph.interaction import build_interaction_graph, graph_partition_objective, valid_two_fragment_partitions


COUNT_OVERHEADS = {"cx": exp(1), "cz": exp(1), "iswap": exp(1), "rzz": exp(1)}


def _record(family: str, num_qubits: int) -> dict[str, object]:
    circuit, audit = ingest_mqt_benchmark(family, num_qubits, representation="native_qpd")
    count_graph = build_interaction_graph(circuit, cost_model="legacy_cx", qpd_overheads=COUNT_OVERHEADS)
    qpd_graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    values = [
        (partition, graph_partition_objective(count_graph, partition), graph_partition_objective(qpd_graph, partition))
        for partition in valid_two_fragment_partitions(num_qubits, num_qubits // 2)
    ]
    min_count = min(count for _, count, _ in values)
    best_qpd_at_count = min(qpd for _, count, qpd in values if abs(count - min_count) <= 1e-9)
    qpd_optimum = min(qpd for _, _, qpd in values)
    return {
        "experiment": "E3_small_native_count_qpd_check",
        "family": family,
        "num_qubits": num_qubits,
        "cost_model": "qiskit_qpd_0.10.0_independent",
        "two_qubit_gate_types": audit.two_qubit_gate_types,
        "minimum_cut_count": min_count,
        "best_qpd_log_at_minimum_cut": best_qpd_at_count,
        "qpd_optimum_log": qpd_optimum,
        "strict_regret": best_qpd_at_count > qpd_optimum + 1e-9,
    }


def main() -> None:
    rows = [_record(family, num_qubits) for family in ("qaoa", "bv", "vqe_real_amp") for num_qubits in (8, 12, 16)]
    output = Path("results/phase11_5_e3_count_qpd_check.json")
    output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(rows), "strict_reversals": sum(row["strict_regret"] for row in rows)}, indent=2))


if __name__ == "__main__":
    main()
