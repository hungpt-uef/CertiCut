"""Phase 6.2 Track A hard-rung checkpoints and controlled A0-A3 ablations."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.benchmark.checkpoints import extract_checkpoints
from certicut.benchmark.instance import BenchmarkInstance
from certicut.benchmark.runner import record_certicut_result, run_track_a
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb


CHECKPOINTS = (0, 1, 5, 10, 30, 100)
FAMILIES = ("community", "nearest_neighbor", "random", "dense", "weighted_random", "noisy_community")


def main() -> None:
    records, checkpoints = [], []
    for n in (24, 26, 32):
        for family in FAMILIES:
            for seed in range(5):
                instance = BenchmarkInstance(family, n, seed)
                graph = build_interaction_graph(instance.circuit())
                for method in ("h2", "h3", "kahip_fast", "phase2_milp", "a0_b0_h0", "a1_b0_h2", "a2_b2s_h0"):
                    records.append(run_track_a(instance, method, node_limit=100).as_dict())
                result = solve_certified_bnb(
                    graph, qmax=instance.qmax, exact_num_fragments=True, node_limit=100,
                    lp_variant="b2s_root", warm_start_variant="h2", collect_profile=True,
                )
                records.append(record_certicut_result(instance, result, result.profile.solve_time_s if result.profile else None).as_dict())
                for checkpoint in extract_checkpoints(result, CHECKPOINTS):
                    checkpoints.append({"instance_id": instance.instance_id, "method": "certicut_b2s_h2", **checkpoint.as_dict()})
    Path("results/phase6_2_track_a_records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    Path("results/phase6_2_checkpoints.jsonl").write_text("".join(json.dumps(r) + "\n" for r in checkpoints), encoding="utf-8")
    print(json.dumps({"instances": 90, "method_runs": len(records), "checkpoints": len(checkpoints), "errors": sum(r["status"] == "error" for r in records)}, indent=2))


if __name__ == "__main__":
    main()
