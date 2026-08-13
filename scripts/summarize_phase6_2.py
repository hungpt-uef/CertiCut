"""Derive Phase 6.2 tables solely from raw JSONL benchmark artifacts."""

from __future__ import annotations

import json
from math import exp
from pathlib import Path
import statistics


def main() -> None:
    records = [json.loads(line) for line in Path("results/phase6_2_track_a_records.jsonl").read_text(encoding="utf-8").splitlines()]
    checkpoints = [json.loads(line) for line in Path("results/phase6_2_checkpoints.jsonl").read_text(encoding="utf-8").splitlines()]
    oracle = {record["instance_id"]: record["objective_log"] for record in records if record["method"] == "phase2_milp" and record["status"] == "optimal"}
    heuristic = {}
    for method in ("h2", "h3", "kahip_fast"):
        factors = sorted(exp(record["objective_log"] - oracle[record["instance_id"]]) for record in records if record["method"] == method and record["instance_id"] in oracle)
        heuristic[method] = {"oracle_subset": len(factors), "optimal_hits": sum(value <= 1 + 1e-9 for value in factors), "median_factor": statistics.median(factors), "p90_factor": factors[int(.9 * (len(factors) - 1))], "median_runtime_s": statistics.median(record["runtime_s"] for record in records if record["method"] == method)}
    ablation = {}
    for method in ("a0_b0_h0", "a1_b0_h2", "a2_b2s_h0", "certicut_b2s_h2"):
        subset = [record for record in records if record["method"] == method]
        ablation[method] = {"proven_optimal": sum(record["proven_optimal"] is True for record in subset), "node_limited": sum(record["status"] == "node_limit" for record in subset), "median_nodes": statistics.median(record["expanded_nodes"] for record in subset), "median_root_time_s": statistics.median(record["root_time_s"] for record in subset), "median_tree_time_s": statistics.median(record["tree_time_s"] for record in subset)}
    checkpoint_summary = {}
    for limit in (0, 1, 5, 10, 30, 100):
        subset = [record for record in checkpoints if record["node_limit"] == limit]
        factors = sorted(record["certified_factor"] for record in subset)
        checkpoint_summary[str(limit)] = {"proven_optimal": sum(record["proven_optimal"] for record in subset), "at_most_1_01": sum(value <= 1.01 for value in factors), "at_most_1_05": sum(value <= 1.05 for value in factors), "at_most_1_10": sum(value <= 1.10 for value in factors), "median_factor": statistics.median(factors), "p90_factor": factors[int(.9 * (len(factors) - 1))]}
    summary = {"instances": len(oracle), "method_runs": len(records), "checkpoint_records": len(checkpoints), "errors": sum(record["status"] == "error" for record in records), "oracle_checkpoint_invariant_violations": sum(not (record["lb_log"] <= oracle[record["instance_id"]] + 1e-8 and oracle[record["instance_id"]] <= record["ub_log"] + 1e-8) for record in checkpoints), "heuristics": heuristic, "ablations": ablation, "checkpoints": checkpoint_summary}
    Path("results/phase6_2_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
