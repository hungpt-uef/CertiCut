"""Shared serializable metrics for matched-objective baseline studies."""

from __future__ import annotations

from typing import Any

from certicut.baselines.common import BaselineResult
from certicut.evaluation.canonical import log10_regret_upper_bound


def matched_baseline_record(
    result: BaselineResult,
    *,
    lower_bound_log: float | None,
    solver_closed: bool,
) -> dict[str, Any]:
    """Label closed-case regret separately from open-case certified upper factors."""
    objective = result.objective_log_cost
    log10_upper = (
        log10_regret_upper_bound(objective, lower_bound_log)
        if objective is not None
        else None
    )
    delta = objective - lower_bound_log if objective is not None and lower_bound_log is not None else None
    return {
        "method": result.method,
        "status": result.status,
        "runtime_s": result.runtime_s,
        "objective_log_cost": objective,
        "fragment_sizes": result.fragment_sizes,
        "partition": result.partition,
        "lower_bound_log": lower_bound_log,
        "solver_closed": solver_closed,
        "delta_log_cost": delta if solver_closed else None,
        "regret_log10": log10_upper if solver_closed else None,
        "certified_upper_factor_log10": log10_upper if not solver_closed else None,
        "cut_count": len(result.cut_instruction_indices),
        "notes": result.notes,
    }


def summarize_matched_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute descriptive matched-baseline statistics without mixing open bounds."""
    by_method: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_method.setdefault(record["method"], []).append(record)
    return {
        method: _summary(method_records)
        for method, method_records in sorted(by_method.items())
    }


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [record["regret_log10"] for record in records if record["regret_log10"] is not None]
    deltas = [record["delta_log_cost"] for record in records if record["delta_log_cost"] is not None]
    runtimes = [record["runtime_s"] for record in records]
    return {
        "records": len(records),
        "feasible": sum(record["status"] == "feasible" for record in records),
        "closed_comparisons": len(closed),
        "optimal_on_closed": sum(value <= 1e-10 for value in closed),
        "median_delta_log_cost": _quantile(deltas, 0.5),
        "p90_delta_log_cost": _quantile(deltas, 0.9),
        "maximum_delta_log_cost": max(deltas) if deltas else None,
        "median_log10_regret": _quantile(closed, 0.5),
        "p90_log10_regret": _quantile(closed, 0.9),
        "maximum_log10_regret": max(closed) if closed else None,
        "median_runtime_s": _quantile(runtimes, 0.5),
        "p90_runtime_s": _quantile(runtimes, 0.9),
    }


def _quantile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower, upper = int(index), min(int(index) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)
