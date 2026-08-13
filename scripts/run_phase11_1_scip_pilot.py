"""Phase 11.1 core independent-QPD SCIP formulation audit on hard synthetic corpus."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.scip_core import solve_scip_core


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    records = []
    # Same deterministic family/size/seed grid as Phase 6.2's 90-instance hard rung.
    for family in ("community", "nearest_neighbor", "random", "dense", "weighted_random", "noisy_community"):
        for n in (16, 20, 24):
            for seed in range(5):
                graph = build_interaction_graph(make_benchmark_circuit(family, n, seed))
                for variant in ("g0_basic", "g1_cardinality", "g2_b2s"):
                    result = solve_scip_core(graph, variant=variant, time_limit_s=2.0)
                    records.append({"method": variant, "family": family, "n": n, "seed": seed, **result.as_dict()})
                started = perf_counter()
                certicut = solve_certified_bnb(graph, qmax=n // 2, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant="h2", time_limit_s=2.0)
                elapsed = perf_counter() - started
                cert = certicut.certificate
                records.append({
                    "method": "certicut_b2s_h2", "family": family, "n": n, "seed": seed,
                    "status": certicut.status, "primal_bound": cert.upper_bound_log if cert else None,
                    "dual_bound": cert.lower_bound_log if cert else None,
                    "factor": cert.overhead_factor_bound if cert else None,
                    "proven_optimal": cert.proven_optimal if cert else False,
                    "nodes": certicut.expanded_nodes, "lp_iterations": None,
                    "actual_runtime_s": elapsed,
                })
                print(f"[{family} n={n} s={seed}] done")
    destination = ROOT / "results" / "phase11_1_scip_hard90_pilot.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
