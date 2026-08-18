"""Regenerate E12-D certificate profiles from the frozen six-cell protocol."""

from __future__ import annotations

import json
import os
from math import log
from pathlib import Path
import sys

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.k_partition import solve_scip_k_partition


OUTPUT = ROOT / "results" / "upgrade_2026" / "e12_hybrid_certificate" / "dual_bound_profiles" / "records.json"
CELLS = ((40, 3), (40, 4), (40, 5), (60, 3), (60, 4), (60, 5))
BUDGETS = (10.0, 30.0, 60.0)
PROFILES = {
    "default": {"cross_pair_strengthening": False},
    "cardinality_root": {"cross_pair_strengthening": True},
}


def capacities(n: int, k: int) -> tuple[int, ...]:
    base, remainder = divmod(n, k)
    return tuple(base + (index < remainder) for index in range(k))


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    records = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else []
    completed = {(record["n"], record["K"], record["profile"], record["budget_s"]) for record in records}
    for n, k in CELLS:
        graph = build_interaction_graph(
            make_heterogeneous_qpd_circuit("random_matching", n, 20260812),
            cost_model="qiskit_qpd",
        )
        capacity = capacities(n, k)
        for profile, options in PROFILES.items():
            for budget_s in BUDGETS:
                key = n, k, profile, budget_s
                if key in completed:
                    continue
                result = solve_scip_k_partition(
                    graph,
                    num_fragments=k,
                    lower_capacities=capacity,
                    upper_capacities=capacity,
                    time_limit_s=budget_s,
                    symmetry_breaking=True,
                    **options,
                )
                certificate = result.certificate
                log10_factor = (
                    log(certificate.overhead_factor_bound, 10)
                    if certificate is not None and certificate.overhead_factor_bound is not None
                    else None
                )
                records.append({
                    "experiment": "E12-D",
                    "n": n,
                    "K": k,
                    "seed": 0,
                    "generator_seed": 20260812,
                    "capacities": capacity,
                    "profile": profile,
                    "profile_options": options,
                    "budget_s": budget_s,
                    "status": result.status,
                    "runtime_s": result.runtime_s,
                    "nodes": result.nodes,
                    "lp_iterations": result.lp_iterations,
                    "lower_bound_log": certificate.lower_bound_log if certificate else None,
                    "upper_bound_log": certificate.upper_bound_log if certificate else None,
                    "log10_F": log10_factor,
                    "solver_closed": bool(certificate and certificate.overhead_factor_bound <= 1.0 + result.tolerance),
                    "scip_version": "9.2.4",
                })
                OUTPUT.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
                print(f"[{profile} n={n} K={k} t={budget_s:g}] {result.status}; log10 F={log10_factor}", flush=True)


if __name__ == "__main__":
    main()
