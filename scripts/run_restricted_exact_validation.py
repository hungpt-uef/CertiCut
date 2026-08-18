"""Validate graph aggregation against a direct restricted gate-only exact oracle."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.baselines.restricted_exact import solve_restricted_gate_only_exact
from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.k_partition import solve_scip_k_partition


def _capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    records = []
    for family in ("random_matching", "community_matching", "weighted_repeat"):
        for n, k, seed in ((6, 2, 0), (8, 2, 1), (8, 3, 2), (10, 2, 0)):
            capacities = _capacities(n, k)
            graph = build_interaction_graph(
                make_heterogeneous_qpd_circuit(family, n, 20260812 + seed), cost_model="qiskit_qpd",
            )
            direct = solve_restricted_gate_only_exact(graph, capacities=capacities)
            scip = solve_scip_k_partition(
                graph, num_fragments=k, lower_capacities=capacities, upper_capacities=capacities, time_limit_s=30.0,
            )
            scip_cost = scip.objective_log_cost
            records.append({
                "family": family, "num_qubits": n, "K": k, "seed": seed, "capacities": capacities,
                "direct_gate_log_cost": direct.direct_gate_log_cost,
                "graph_log_cost": direct.graph_log_cost,
                "scip_log_cost": scip_cost,
                "direct_graph_abs_error": abs(direct.direct_gate_log_cost - direct.graph_log_cost),
                "direct_scip_abs_error": abs(direct.direct_gate_log_cost - scip_cost) if scip_cost is not None else None,
                "scip_status": scip.status,
            })
    output = ROOT / "results" / "upgrade_2026" / "e16_baseline_suite" / "restricted_exact_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
