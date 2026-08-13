"""Summarize frozen E8 equal-shot raw estimator distributions."""

from __future__ import annotations

import argparse
import json
from math import sqrt
from pathlib import Path
import random
from statistics import fmean, median


BOOTSTRAP_SEED = 20260812
BOOTSTRAP_REPLICATES = 10_000


def _rmse(values: list[float], reference: float) -> float:
    return sqrt(fmean((value - reference) ** 2 for value in values))


def _bootstrap_rmse_difference(count: list[float], qpd: list[float], reference: float) -> tuple[float, float]:
    if len(count) != len(qpd):
        raise ValueError("paired E8 distributions must have equal length")
    generator = random.Random(BOOTSTRAP_SEED)
    n = len(count)
    differences = []
    for _ in range(BOOTSTRAP_REPLICATES):
        indices = [generator.randrange(n) for _ in range(n)]
        differences.append(_rmse([count[index] for index in indices], reference) - _rmse([qpd[index] for index in indices], reference))
    differences.sort()
    return differences[int(0.025 * (BOOTSTRAP_REPLICATES - 1))], differences[int(0.975 * (BOOTSTRAP_REPLICATES - 1))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("results/phase12_e8_finite_shot.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("results/phase12_e8_finite_shot_summary.json"))
    args = parser.parse_args()
    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines()]
    output = []
    for record in records:
        count, qpd = record["comparison"]["plans"]
        observables = []
        for count_observable, qpd_observable in zip(count["observables"], qpd["observables"], strict=True):
            reference = count_observable["uncut_expectation"]
            count_values = count_observable["estimator_distribution"]
            qpd_values = qpd_observable["estimator_distribution"]
            interval = _bootstrap_rmse_difference(count_values, qpd_values, reference)
            observables.append({
                "observable": count_observable["observable"],
                "reference": reference,
                "count": {
                    "mean": fmean(count_values), "bias": count_observable["bias"],
                    "variance": count_observable["estimator_standard_deviation"] ** 2,
                    "rmse": count_observable["rmse"],
                    "median_absolute_error": median(abs(value - reference) for value in count_values),
                },
                "qpd": {
                    "mean": fmean(qpd_values), "bias": qpd_observable["bias"],
                    "variance": qpd_observable["estimator_standard_deviation"] ** 2,
                    "rmse": qpd_observable["rmse"],
                    "median_absolute_error": median(abs(value - reference) for value in qpd_values),
                },
                "paired_rmse_improvement_count_minus_qpd": count_observable["rmse"] - qpd_observable["rmse"],
                "bootstrap_95pct_interval": interval,
            })
        output.append({
            "case_id": record["case_id"], "witness": record["witness"],
            "total_shots_per_seed": record["comparison"]["total_shots_per_seed"],
            "qpd_samples_per_seed": record["comparison"]["qpd_samples_per_seed"],
            "trials": len(record["comparison"]["seeds"]),
            "plan_log_costs": [count["optimizer_log_cost"], qpd["optimizer_log_cost"]],
            "plan_overheads": [count["qpd_overhead"], qpd["qpd_overhead"]],
            "observables": observables,
        })
    args.output.write_text(json.dumps({
        "experiment": "E8_finite_shot_equal_budget_reversal", "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES, "records": output,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
