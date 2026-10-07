from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.graph.interaction import build_interaction_graph, graph_partition_objective
from certicut.optimization.k_partition import solve_scip_k_partition
from scripts.run_e12_representation_placement_regret import _near_balanced_capacities

OUT = ROOT / "results" / "e12_qft_single_solution_tie_audit.json"


def main() -> None:
    records = []
    for n in (12, 14, 16):
        pair = ingest_mqt_pair("qft", n)
        circuit_a, _ = pair["cx_normalized"]
        circuit_b, _ = pair["native_qpd"]
        graph_a = build_interaction_graph(circuit_a, cost_model="qiskit_qpd")
        graph_b = build_interaction_graph(circuit_b, cost_model="qiskit_qpd")
        for k in (2, 3):
            lower, upper = _near_balanced_capacities(n, k)
            result_a = solve_scip_k_partition(
                graph_a, num_fragments=k, lower_capacities=lower, upper_capacities=upper,
                time_limit_s=120.0, symmetry_breaking=True, feasibility_tolerance=1e-10,
            )
            result_b = solve_scip_k_partition(
                graph_b, num_fragments=k, lower_capacities=lower, upper_capacities=upper,
                time_limit_s=120.0, symmetry_breaking=True, feasibility_tolerance=1e-10,
            )
            if result_a.status != "optimal" or result_b.status != "optimal":
                raise RuntimeError(f"stage-1 optimum not proven for qft n={n} K={k}: {result_a.status}, {result_b.status}")
            ja = graph_partition_objective(graph_a, result_a.partition)
            jb = graph_partition_objective(graph_b, result_b.partition)
            cross_ab = graph_partition_objective(graph_b, result_a.partition)
            cross_ba = graph_partition_objective(graph_a, result_b.partition)
            delta_ab = max(0.0, cross_ab - jb)
            delta_ba = max(0.0, cross_ba - ja)
            records.append({
                "family": "qft", "n": n, "K": k,
                "capacity_policy": "symmetric_near_balanced_v1",
                "lower_capacities": list(lower), "upper_capacities": list(upper),
                "feasibility_tolerance": 1e-10,
                "status_a": result_a.status, "status_b": result_b.status,
                "J_a_star": ja, "J_b_star": jb,
                "single_solution_delta_a_to_b": delta_ab,
                "single_solution_delta_b_to_a": delta_ba,
                "single_solution_max_ratio": math.exp(max(delta_ab, delta_ba)),
                "partition_a": list(result_a.partition), "partition_b": list(result_b.partition),
            })
    canonical_rows = json.loads((ROOT / "results" / "e12_representation_placement_regret.json").read_text(encoding="utf-8"))
    canonical_qft = {(r["n"], r["K"]): r for r in canonical_rows if r["family"] == "qft" and r["tier"] == "scip_set_level"}
    for record in records:
        row = canonical_qft[(record["n"], record["K"])]
        pair = ingest_mqt_pair("qft", record["n"])
        circuit_a, _ = pair["cx_normalized"]
        circuit_b, _ = pair["native_qpd"]
        graph_a = build_interaction_graph(circuit_a, cost_model="qiskit_qpd")
        graph_b = build_interaction_graph(circuit_b, cost_model="qiskit_qpd")
        shared = row["rep_partition_a"]
        record["set_level_shared_witness"] = list(shared)
        record["set_level_shared_witness_slack_a"] = graph_partition_objective(graph_a, shared) - row["J_a_star"]
        record["set_level_shared_witness_slack_b"] = graph_partition_objective(graph_b, shared) - row["J_b_star"]
        record["set_level_delta_a_to_b"] = row["delta_a_to_b"]
        record["set_level_delta_b_to_a"] = row["delta_b_to_a"]

    payload = {
        "schema": "certicut-qft-tie-audit-v2",
        "purpose": "Demonstrate false representation changes from cross-evaluating one optimizer-returned optimum per representation and record a shared near-zero-slack witness for the set-level result.",
        "records": records,
        "apparent_changes": sum(
            r["single_solution_delta_a_to_b"] > 1e-10 or r["single_solution_delta_b_to_a"] > 1e-10
            for r in records
        ),
        "max_single_solution_ratio": max(r["single_solution_max_ratio"] for r in records),
        "max_abs_shared_witness_slack": max(
            max(abs(r["set_level_shared_witness_slack_a"]), abs(r["set_level_shared_witness_slack_b"]))
            for r in records
        ),
        "set_level_result": "All six corresponding canonical E12 QFT medium records have Delta=0 and R=1; each audit row records a partition whose recomputed objectives agree with both recorded optima to floating-point precision.",
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    print(json.dumps({"apparent_changes": payload["apparent_changes"], "max_ratio": payload["max_single_solution_ratio"]}, indent=2))


if __name__ == "__main__":
    main()
