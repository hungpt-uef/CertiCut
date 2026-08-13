"""Derive paper E1 wall-clock certificate and memory summaries from isolated raw records."""

from __future__ import annotations

import json
from pathlib import Path
import statistics


BUDGETS = (0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)


def main() -> None:
    rows = [json.loads(line) for line in Path("results/phase6_6b_e1_certicut.jsonl").read_text(encoding="utf-8").splitlines()]
    snapshots = []
    for row in rows:
        timeline = row.get("timeline", [])
        for budget in BUDGETS:
            eligible = [event for event in timeline if event["elapsed_s"] <= budget]
            if not eligible:
                snapshots.append({"family": row["family"], "num_qubits": row["num_qubits"], "seed": row["seed"], "budget_s": budget, "actual_run_time_s": row["algorithm_runtime_s"], "status": row["status"], "certificate_available": False, "lb_log": None, "ub_log": None, "factor": None, "bound_closed": False, "proven_optimal": False, "phase": None, "expanded_nodes": 0})
                continue
            event = eligible[-1]
            snapshots.append({"family": row["family"], "num_qubits": row["num_qubits"], "seed": row["seed"], "budget_s": budget, "actual_run_time_s": row["algorithm_runtime_s"], "status": row["status"], "certificate_available": True, "lb_log": event["global_lb"], "ub_log": event["incumbent_ub"], "factor": event["overhead_factor_bound"], "bound_closed": (event["additive_log_gap"] or 0) <= 1e-9, "proven_optimal": (event["additive_log_gap"] or 0) <= 1e-9 and event["open_nodes"] == 0, "phase": event["event"], "expanded_nodes": event["expanded_nodes"]})
    Path("results/phase6_6b_e1_wallclock_checkpoints.jsonl").write_text("".join(json.dumps(row) + "\n" for row in snapshots), encoding="utf-8")
    checkpoint_summary = {}
    for budget in BUDGETS:
        subset = [row for row in snapshots if row["budget_s"] == budget]
        available = [row for row in subset if row["certificate_available"]]
        factors = sorted(row["factor"] for row in available)
        checkpoint_summary[str(budget)] = {"certificate_available": len(available), "proven_optimal": sum(row["proven_optimal"] for row in available), "bound_closed": sum(row["bound_closed"] for row in available), "at_most_1_01": sum(value <= 1.01 for value in factors), "at_most_1_05": sum(value <= 1.05 for value in factors), "at_most_1_10": sum(value <= 1.10 for value in factors), "median_factor": statistics.median(factors) if factors else None, "p90_factor": factors[int(.9 * (len(factors) - 1))] if factors else None}
    sizes = {}
    for n in sorted({row["num_qubits"] for row in rows}):
        subset = [row for row in rows if row["num_qubits"] == n]
        peaks = sorted(row["peak_rss_mb"] for row in subset if row["peak_rss_mb"] is not None)
        sizes[str(n)] = {"records": len(subset), "optimal": sum(row["status"] == "optimal" for row in subset), "median_end_to_end_s": statistics.median(row["end_to_end_algorithm_time_s"] for row in subset), "median_optimizer_s": statistics.median(row["optimizer_runtime_s"] for row in subset), "median_preprocessing_s": statistics.median(row["preprocessing_time_s"] for row in subset), "median_peak_rss_mb": statistics.median(peaks), "p90_peak_rss_mb": peaks[int(.9 * (len(peaks) - 1))]}
    summary = {"records": len(rows), "statuses": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})}, "wallclock_checkpoints": checkpoint_summary, "by_size": sizes}
    Path("results/phase6_6b_e1_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
