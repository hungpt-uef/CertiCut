"""Choose KaHIP mode on a calibration subset before Phase 6.2 final matrix."""

from __future__ import annotations

import json
from math import exp
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.baselines.kahip import solve_kahip
from certicut.benchmark.instance import BenchmarkInstance
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition


def main() -> None:
    records = []
    for n in (24, 26):
        for family in ("random", "dense", "weighted_random"):
            for seed in range(3):
                instance = BenchmarkInstance(family, n, seed)
                graph = build_interaction_graph(instance.circuit())
                oracle = solve_exact_partition(graph, num_fragments=2, qmax=instance.qmax, exact_num_fragments=True)
                for mode in ("fast", "eco", "strong"):
                    result = solve_kahip(graph, seed=seed, mode=mode)
                    excess = ((result.objective_log_cost or 0) - (oracle.objective_log_cost or 0)) if oracle.status == "optimal" else None
                    records.append({"instance_id": instance.instance_id, "mode": mode, "status": result.status, "runtime_s": result.runtime_s, "objective_log": result.objective_log_cost, "oracle_log": oracle.objective_log_cost, "excess_log": excess, "factor": exp(excess) if excess is not None else None})
    Path("results/phase6_2_kahip_calibration.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    summary = {
        mode: {
            "records": len(subset := [record for record in records if record["mode"] == mode]),
            "optimal_hits": sum((record["excess_log"] or 0) <= 1e-9 for record in subset),
            "median_factor": statistics.median(record["factor"] for record in subset if record["factor"] is not None),
            "median_runtime_s": statistics.median(record["runtime_s"] for record in subset),
        }
        for mode in ("fast", "eco", "strong")
    }
    Path("results/phase6_2_kahip_calibration_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
