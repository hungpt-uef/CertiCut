"""Find sampling/routing trade-offs under the CertiCut 5% Gamma budget."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.k_partition import solve_lexicographic_k_partition, solve_scip_k_partition


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    records = []
    for family in ("random_matching", "community_matching", "dense_shuffled"):
        for n, k in ((20, 2), (20, 3), (32, 2), (32, 4)):
            circuit = make_heterogeneous_qpd_circuit(family, n, 20260812)
            graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
            capacity = _capacities(n, k)
            # Logical-index separation is a stated topology-free proxy, used only
            # to force a reproducible tie/trade-off before real placement MILP.
            routing_costs = tuple(float(max(0, abs(edge.u - edge.v) - 1) * edge.gate_count) for edge in graph.edges)
            sampling = solve_scip_k_partition(
                graph, num_fragments=k, lower_capacities=capacity, upper_capacities=capacity, time_limit_s=20.0
            )
            lexicographic = solve_lexicographic_k_partition(
                graph, num_fragments=k, lower_capacities=capacity, upper_capacities=capacity,
                routing_costs=routing_costs, allowed_gamma_factor=1.05, time_limit_s=20.0,
            )
            routing_at_sampling = sum(
                routing_costs[index] for index, edge in enumerate(graph.edges)
                if sampling.partition is not None and sampling.partition[edge.u] == sampling.partition[edge.v]
            )
            records.append({
                "family": family, "num_qubits": n, "K": k, "capacities": capacity,
                "sampling_status": sampling.status,
                "sampling_log_gamma": sampling.objective_log_cost,
                "sampling_gamma": sampling.gamma,
                "routing_at_sampling_optimum": routing_at_sampling,
                "lexicographic_status": lexicographic.routing_status,
                "lexicographic_log_gamma": lexicographic.objective_log_cost,
                "lexicographic_gamma": lexicographic.gamma,
                "lexicographic_routing": lexicographic.routing_surrogate_cost,
                "allowed_gamma_factor": lexicographic.allowed_gamma_factor,
                "actual_gamma_factor": (lexicographic.gamma / sampling.gamma) if lexicographic.gamma and sampling.gamma else None,
                "runtime_s": lexicographic.runtime_s,
            })
            print(f"[{family} n={n} K={k}] routing {routing_at_sampling} -> {lexicographic.routing_surrogate_cost}; Gamma factor={records[-1]['actual_gamma_factor']}")
    path = ROOT / "results" / "e7_k_lexicographic_routing.json"
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
