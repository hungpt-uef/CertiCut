"""Algorithm-derived capacitated K-way independent-QPD SCIP matrix."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.circuits.ingestion import ingest_mqt_benchmark
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.k_partition import solve_scip_k_partition


FAMILIES = ("qaoa", "qft", "qpeexact", "draper_qft_adder", "vqe")
SIZES = (20, 24, 32)
FRAGMENTS = (2, 3, 4)


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    destination = ROOT / "results" / "e10_algorithmic_kway.jsonl"
    with destination.open("w", encoding="utf-8") as stream:
        for family in FAMILIES:
            for n in SIZES:
                try:
                    circuit, audit = ingest_mqt_benchmark(family, n, representation="native_qpd")
                except Exception as error:
                    stream.write(json.dumps({"family": family, "num_qubits": n, "status": "ingestion_failed", "error": str(error)}) + "\n")
                    continue
                graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
                for k in FRAGMENTS:
                    capacity = _capacities(n, k)
                    result = solve_scip_k_partition(
                        graph, num_fragments=k, lower_capacities=capacity, upper_capacities=capacity, time_limit_s=10.0
                    )
                    certificate = result.certificate
                    row = {"family": family, "num_qubits": n, "K": k, "capacities": capacity,
                           "status": result.status, "runtime_s": result.runtime_s, "nodes": result.nodes,
                           "two_qubit_gates": sum(edge.gate_count for edge in graph.edges), "interaction_edges": len(graph.edges),
                           "objective_log_cost": result.objective_log_cost, "gamma": result.gamma,
                           "factor": certificate.overhead_factor_bound if certificate else None,
                           "audit_fingerprint": audit.circuit_fingerprint}
                    stream.write(json.dumps(row) + "\n")
                    print(f"[{family} n={n} K={k}] {result.status}; F={row['factor']}; t={result.runtime_s:.2f}s")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
