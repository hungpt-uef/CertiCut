"""Profile vanilla Phase 3A B&B on deterministic optimizer-only circuits."""

from __future__ import annotations

import json
from math import ceil
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb


SIZES = (8, 10, 12, 14, 16, 20, 24)
FAMILIES = ("random", "nearest_neighbor", "qaoa_ring", "dense", "community")
SEEDS = range(5)
NODE_LIMIT = 50


def main() -> None:
    output_dir = Path("results")
    records_path = output_dir / "phase3b_b0_records.jsonl"
    records = []
    with records_path.open("w", encoding="utf-8") as output:
        for num_qubits in SIZES:
            for family_index, family in enumerate(FAMILIES):
                for seed in SEEDS:
                    circuit = make_benchmark_circuit(family, num_qubits, 1000 * family_index + seed)
                    graph = build_interaction_graph(circuit)
                    result = solve_certified_bnb(
                        graph,
                        qmax=ceil(num_qubits / 2),
                        exact_num_fragments=True,
                        node_limit=NODE_LIMIT,
                        collect_profile=True,
                    )
                    assert result.certificate is not None and result.profile is not None
                    record = {
                        "family": family,
                        "seed": seed,
                        "num_qubits": num_qubits,
                        "num_edges": len(graph.edges),
                        "qmax": ceil(num_qubits / 2),
                        "node_limit": NODE_LIMIT,
                        "status": result.status,
                        "final_objective_log": result.certificate.upper_bound_log,
                        "final_lb_log": result.certificate.lower_bound_log,
                        "final_log_gap": result.certificate.additive_log_gap,
                        "final_overhead_factor": result.certificate.overhead_factor_bound,
                        "expanded_nodes": result.expanded_nodes,
                        **result.profile.__dict__,
                    }
                    record["root_bound_recovery_ratio"] = (
                        record["root_lp_lb"] / record["final_objective_log"]
                        if record["final_objective_log"] > 0 and result.status == "optimal"
                        else None
                    )
                    records.append(record)
                    output.write(json.dumps(record) + "\n")
    summary = _summarize(records)
    (output_dir / "phase3b_b0_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def _summarize(records: list[dict[str, object]]) -> dict[str, object]:
    def median(metric: str, subset: list[dict[str, object]]) -> float:
        return float(statistics.median(float(record[metric]) for record in subset))

    solved = [record for record in records if record["status"] == "optimal"]
    return {
        "config": {
            "sizes": SIZES,
            "families": FAMILIES,
            "seeds_per_family_size": len(SEEDS),
            "instance_count": len(records),
            "node_limit": NODE_LIMIT,
            "exact_num_fragments": True,
            "qmax": "ceil(n/2)",
        },
        "status_counts": {status: sum(record["status"] == status for record in records) for status in sorted({str(record["status"]) for record in records})},
        "overall_medians": {
            "root_lp_lb": median("root_lp_lb", records),
            "initial_ub": median("initial_ub", records),
            "root_gap_log": median("root_gap_log", records),
            "root_factor_bound": median("root_factor_bound", records),
            "expanded_nodes": median("expanded_nodes", records),
            "generated_nodes": median("generated_nodes", records),
            "pruned_by_bound": median("pruned_by_bound", records),
            "max_frontier_size": median("max_frontier_size", records),
            "lp_solve_count": median("lp_solve_count", records),
            "lp_time_total_s": median("lp_time_total_s", records),
            "solve_time_s": median("solve_time_s", records),
        },
        "completed_instances": {
            "count": len(solved),
            "median_root_bound_recovery_ratio": median("root_bound_recovery_ratio", solved),
        },
        "by_family": {
            family: {
                "instances": len(subset := [record for record in records if record["family"] == family]),
                "median_root_factor_bound": median("root_factor_bound", subset),
                "median_expanded_nodes": median("expanded_nodes", subset),
                "node_limited": sum(record["status"] == "node_limit" for record in subset),
                "median_root_bound_recovery_ratio_completed": median(
                    "root_bound_recovery_ratio",
                    [record for record in subset if record["root_bound_recovery_ratio"] is not None],
                ),
            }
            for family in FAMILIES
        },
    }


if __name__ == "__main__":
    main()
