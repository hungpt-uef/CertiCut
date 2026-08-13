"""Controlled B0/B1/B2 profiling plus primal-dual diagnostic decomposition."""

from __future__ import annotations

import json
from math import ceil, exp
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
VARIANTS = ("b0", "b1_compact", "b2_metric")


def main() -> None:
    records: list[dict[str, object]] = []
    output = Path("results/phase3b_variant_records.jsonl")
    with output.open("w", encoding="utf-8") as stream:
        for n in SIZES:
            for family_index, family in enumerate(FAMILIES):
                for seed in SEEDS:
                    graph = build_interaction_graph(
                        make_benchmark_circuit(family, n, 1000 * family_index + seed)
                    )
                    for variant in VARIANTS:
                        result = solve_certified_bnb(
                            graph, qmax=ceil(n / 2), exact_num_fragments=True,
                            node_limit=NODE_LIMIT, collect_profile=True, lp_variant=variant,
                        )
                        assert result.profile is not None and result.certificate is not None
                        profile = result.profile
                        record: dict[str, object] = {
                            "variant": variant, "family": family, "seed": seed,
                            "num_qubits": n, "num_edges": len(graph.edges), "status": result.status,
                            "expanded_nodes": result.expanded_nodes,
                            "final_lb_log": result.certificate.lower_bound_log,
                            "final_ub_log": result.certificate.upper_bound_log,
                            **profile.__dict__,
                        }
                        if variant == "b0" and result.status == "optimal":
                            optimum = result.certificate.upper_bound_log
                            primal_log = profile.initial_ub - optimum
                            dual_log = optimum - profile.root_lp_lb
                            record.update({
                                "optimum_log": optimum,
                                "initial_primal_log_gap": primal_log,
                                "initial_dual_log_gap": dual_log,
                                "initial_primal_factor": exp(primal_log),
                                "initial_dual_factor": exp(dual_log),
                                "factor_decomposition_relative_error": abs(
                                    1.0 - (exp(primal_log) * exp(dual_log)) / profile.root_factor_bound
                                ),
                            })
                        records.append(record)
                        stream.write(json.dumps(record) + "\n")
    summary = _summarize(records)
    Path("results/phase3b_variant_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _summarize(records: list[dict[str, object]]) -> dict[str, object]:
    def median(subset: list[dict[str, object]], metric: str) -> float:
        return float(statistics.median(float(record[metric]) for record in subset))

    def variant_summary(subset: list[dict[str, object]]) -> dict[str, object]:
        return {
            "instances": len(subset),
            "optimal": sum(record["status"] == "optimal" for record in subset),
            "node_limited": sum(record["status"] == "node_limit" for record in subset),
            "median_root_lb": median(subset, "root_lp_lb"),
            "median_root_factor": median(subset, "root_factor_bound"),
            "median_nodes": median(subset, "expanded_nodes"),
            "median_lp_variables": median(subset, "root_lp_variable_count"),
            "median_lp_constraints": median(subset, "root_lp_constraint_count"),
            "median_lp_time_s": median(subset, "lp_time_total_s"),
            "median_solve_time_s": median(subset, "solve_time_s"),
        }

    diagnostics = [r for r in records if r["variant"] == "b0" and r.get("optimum_log") is not None]
    return {
        "config": {"instances_per_variant": 175, "node_limit": NODE_LIMIT, "variants": VARIANTS},
        "overall": {variant: variant_summary([r for r in records if r["variant"] == variant]) for variant in VARIANTS},
        "b0_primal_dual_completed": _diagnostic_summary(diagnostics, median),
        "by_family": {
            family: {
                "b0_primal_dual_completed": _diagnostic_summary(
                    [r for r in diagnostics if r["family"] == family], median
                ),
                **{
                    variant: variant_summary(
                        [r for r in records if r["family"] == family and r["variant"] == variant]
                    )
                    for variant in VARIANTS
                },
            }
            for family in FAMILIES
        },
    }


def _diagnostic_summary(records: list[dict[str, object]], median) -> dict[str, object]:
    return {
        "instances": len(records),
        "median_primal_factor": median(records, "initial_primal_factor"),
        "median_dual_factor": median(records, "initial_dual_factor"),
        "max_factor_decomposition_relative_error": max(
            float(record["factor_decomposition_relative_error"]) for record in records
        ),
    }


if __name__ == "__main__":
    main()
