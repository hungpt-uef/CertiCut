"""Strong-branching structural comparison on B2S-R H2 hard instances."""

from __future__ import annotations

import json
from math import ceil
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.lp import solve_b2_separated_lp
from scripts.run_phase3c import _stress_circuit


VARIANTS = (("mf", None), ("sb4", 4), ("sb8", 8), ("sb_full", None))


def main() -> None:
    records, states = [], []
    # SB-Full is an expert upper baseline; start at n=26 before n=32+ cost expansion.
    for n in (26,):
        for regime_index, regime in enumerate(("random_p10", "random_p50", "community_noise", "weighted_random")):
            for seed in range(2):
                graph = build_interaction_graph(_stress_circuit(regime, n, 10000 * regime_index + seed))
                qmax = ceil(n / 2)
                root = solve_b2_separated_lp(graph, qmax=qmax, exact_num_fragments=True, policy="top_k", top_k=500)
                if root.relaxation.fractional_variable_count == 0:
                    continue
                for name, k in VARIANTS:
                    rule = "mf" if name == "mf" else "strong"
                    result = solve_certified_bnb(
                        graph, qmax=qmax, exact_num_fragments=True, node_limit=30, collect_profile=True,
                        lp_variant="b2s_root", warm_start_variant="h2", branching_rule=rule,
                        strong_branching_k=k, collect_strong_branching_states=rule == "strong",
                    )
                    assert result.profile is not None and result.certificate is not None
                    profile = result.profile
                    record = {
                        "instance_id": f"{regime}-{seed}-{n}", "regime": regime, "seed": seed, "num_qubits": n,
                        "variant": name, "status": result.status, "expanded_nodes": result.expanded_nodes,
                        "final_log_gap": result.certificate.additive_log_gap, **profile.__dict__,
                    }
                    records.append(record)
                    for state in result.strong_branching_states:
                        states.append({"instance_id": record["instance_id"], **state})
    Path("results/phase4_records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    Path("results/strong_branching_states.jsonl").write_text("".join(json.dumps(s) + "\n" for s in states), encoding="utf-8")
    summary = _summary(records, states)
    Path("results/phase4_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _summary(records, states):
    def stats(variant, metric):
        values = sorted(float(r[metric]) for r in records if r["variant"] == variant)
        return {"median": statistics.median(values), "p90": values[int(.9 * (len(values) - 1))], "max": max(values)}
    selected = [s for s in states if s["candidate_scores"]]
    ratios = []
    for state in selected:
        scores = state["candidate_scores"]
        mf = str(min((abs(0.5 - 0.5), int(key)) for key in scores)[1]) if scores else None
        if mf in scores and scores[mf] != 0:
            ratios.append(scores[str(state["selected_variable"])] / scores[mf])
    return {
        "hard_instance_count": len({r["instance_id"] for r in records}),
        "variants": {
            variant: {
                "status_counts": {status: sum(r["variant"] == variant and r["status"] == status for r in records) for status in sorted({r["status"] for r in records if r["variant"] == variant})},
                "nodes": stats(variant, "expanded_nodes"),
                "normal_lp_time_s": stats(variant, "node_lp_time_total_s"),
                "sb_probe_time_s": stats(variant, "sb_probe_time_s"),
                "total_time_s": stats(variant, "solve_time_s"),
                "sb_probe_solves": stats(variant, "sb_probe_lp_solves"),
            }
            for variant, _ in VARIANTS
        },
        "strong_branching_states": len(states),
        "decision_ratio_note": "Raw full scores stored; MF comparison requires exact LP fractionality, deferred to Phase 5 dataset featurization.",
    }


if __name__ == "__main__":
    main()
