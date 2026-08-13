"""Summarize frozen E7 raw records without changing the protocol."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path
from statistics import median


def _p90(values: list[float]) -> float | None:
    return sorted(values)[int(0.9 * (len(values) - 1))] if values else None


def _summary(rows: list[dict], method: str, checkpoint: float) -> dict[str, object]:
    if method == "certicut":
        data = [next(item for item in row["certicut_checkpoints"] if item["wall_time_limit_s"] == checkpoint) for row in rows]
        upper = [item["upper_bound_log"] for item in data]
        lower = [item["lower_bound_log"] for item in data]
        factors = [item["factor"] for item in data if item["factor"] is not None]
        nodes = [item["expanded_nodes"] for item in data]
        lp_iterations = []
    else:
        data = [next(item for item in row["scip"][method]["checkpoints"] if item["wall_time_limit_s"] == checkpoint) for row in rows]
        upper = [item["upper_bound"] for item in data]
        lower = [item["lower_bound"] for item in data]
        factors = [item["factor"] for item in data if item["factor"] is not None]
        nodes = [item["nodes"] for item in data]
        lp_iterations = [item["lp_iterations"] for item in data]
    return {
        "records": len(data),
        "factor_le_1_01": sum(value <= 1.01 for value in factors),
        "factor_le_1_10": sum(value <= 1.10 for value in factors),
        "closed": sum(value <= 1.0 + 1e-9 for value in factors),
        "median_factor": median(factors) if factors else None,
        "p90_factor": _p90(factors),
        "median_ub_log": median(value for value in upper if value is not None),
        "median_lb_log": median(value for value in lower if value is not None),
        "median_nodes": median(nodes) if nodes else None,
        "median_lp_iterations": median(lp_iterations) if lp_iterations else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/phase12_e7_heterogeneous_scaling.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("results/phase12_e7_heterogeneous_scaling_summary.json"))
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    checkpoints = tuple(rows[0]["checkpoints_s"])
    summary = {
        "experiment": "E7_heterogeneous_qpd_scaling_matched",
        "records": len(rows),
        "checkpoints": {
            str(checkpoint): {method: _summary(rows, method, checkpoint) for method in ("certicut", "g0_basic", "g1_cardinality", "g2_b2s")}
            for checkpoint in checkpoints
        },
    }
    args.output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
