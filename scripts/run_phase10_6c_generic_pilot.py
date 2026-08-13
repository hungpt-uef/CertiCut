"""Matched wall-clock pilot: certified PJ BnB versus generic HiGHS pattern MILP."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from certicut.optimization.pj_bnb import solve_certified_pj_bnb
from certicut.optimization.pj_exact import solve_exact_pj_pattern_milp
from scripts.run_phase10_6a_prevalence import make_circuit


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    records = []
    instances = [
        (8, 3, "random_matching", 0),
        (8, 5, "random_matching", 1),
        (10, 3, "random_matching", 1),
        (10, 5, "ring_even_odd", 0),
    ]
    for n, depth, family, seed in instances:
        circuit = make_circuit(n, depth, 20261060 + 1000 * n + 100 * depth + seed, family)
        for budget in (0.05, 0.2, 1.0):
            started = perf_counter()
            certicut = solve_certified_pj_bnb(circuit, time_limit_s=budget)
            certicut_s = perf_counter() - started
            started = perf_counter()
            # SciPy's public MILP time-limit option provides the generic comparison.
            generic = solve_exact_pj_pattern_milp(circuit, time_limit_s=budget)
            generic_s = perf_counter() - started
            records.append({
                "n": n, "depth": depth, "family": family, "seed": seed, "budget_s": budget,
                "certicut_status": certicut.status,
                "certicut_actual_s": certicut_s,
                "certicut_lb": certicut.certificate.lower_bound_log,
                "certicut_ub": certicut.certificate.upper_bound_log,
                "certicut_factor": certicut.certificate.overhead_factor_bound,
                "generic_status": generic.status,
                "generic_actual_s": generic_s,
                "generic_objective": generic.objective_log_cost,
                "generic_proven": generic.status == "optimal",
            })
            print(f"[n={n} d={depth} {family} t={budget}] C={certicut.status}/{certicut_s:.3f}s F={certicut.certificate.overhead_factor_bound}; G={generic.status}/{generic_s:.3f}s")
    destination = ROOT / "results" / "phase10_6c_generic_pilot.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
