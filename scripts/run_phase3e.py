"""Compare H0-H3 warm starts inside unchanged B2S-R B&B hard core."""

from __future__ import annotations

import json
from math import ceil, exp
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from scripts.run_phase3c import _stress_circuit


def main() -> None:
    records = []
    # n=40 B2S-R tail is already characterized in Phase 3D; isolate heuristic effect cheaply first.
    for n in (26, 32):
        for regime_index, regime in enumerate(("random_p10", "random_p50", "community_noise", "weighted_random")):
            for seed in range(2):
                graph = build_interaction_graph(_stress_circuit(regime, n, 10000 * regime_index + seed))
                qmax = ceil(n / 2)
                root = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, node_limit=0, lp_variant="b2s_root")
                if root.certificate is None or root.certificate.lower_bound_log == root.certificate.upper_bound_log:
                    continue
                for variant in ("h0", "h1", "h2", "h3"):
                    result = solve_certified_bnb(
                        graph, qmax=qmax, exact_num_fragments=True, node_limit=30, collect_profile=True,
                        lp_variant="b2s_root", warm_start_variant=variant,
                    )
                    assert result.profile is not None and result.certificate is not None
                    profile = result.profile
                    records.append({
                        "regime": regime, "seed": seed, "num_qubits": n, "warm_start": variant,
                        "status": result.status, "expanded_nodes": result.expanded_nodes,
                        "initial_ub": profile.initial_ub, "initial_primal_gap_to_final": profile.initial_ub - result.certificate.upper_bound_log,
                        "initial_primal_factor_to_final": exp(profile.initial_ub - result.certificate.upper_bound_log),
                        "final_gap": result.certificate.additive_log_gap, **profile.__dict__,
                    })
    Path("results/phase3e_records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    summary = _summary(records)
    Path("results/phase3e_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _summary(records):
    def stats(variant, metric):
        values = sorted(float(r[metric]) for r in records if r["warm_start"] == variant)
        return {"median": statistics.median(values), "p90": values[int(.9 * (len(values) - 1))], "max": max(values)}
    return {
        "hard_instance_count": len({(r["regime"], r["seed"], r["num_qubits"]) for r in records}),
        "variants": {
            variant: {
                "status_counts": {status: sum(r["warm_start"] == variant and r["status"] == status for r in records) for status in sorted({r["status"] for r in records if r["warm_start"] == variant})},
                "initial_ub": stats(variant, "initial_ub"),
                "primal_factor": stats(variant, "initial_primal_factor_to_final"),
                "warm_start_time_s": stats(variant, "warm_start_time_s"),
                "nodes": stats(variant, "expanded_nodes"),
                "tree_lp_time_s": stats(variant, "node_lp_time_total_s"),
                "total_time_s": stats(variant, "solve_time_s"),
            }
            for variant in ("h0", "h1", "h2", "h3")
        },
    }


if __name__ == "__main__":
    main()
