"""Matched heterogeneous-QPD scaling audit for CertiCut and SCIP.

No exhaustive oracle is used above 16 qubits.  Both methods instead report
their own solver-tolerance UB/LB factor at identical requested wall budgets.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

# Freeze numerical parallelism before importing NumPy/SciPy through CertiCut.
for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_thread_variable] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.heuristics import warm_start_partition
from certicut.optimization.scip_core import solve_scip_core


FAMILIES = ("random_matching", "ring_even_odd", "community_matching", "dense_shuffled", "weighted_repeat")


def _certicut_snapshot(graph, n: int, time_limit_s: float) -> dict[str, object]:
    result = solve_certified_bnb(
        graph, qmax=n // 2, exact_num_fragments=True, time_limit_s=time_limit_s,
        lp_variant="b2s_root", warm_start_variant="h2", collect_profile=True,
    )
    certificate = result.certificate
    return {
        "wall_time_limit_s": time_limit_s,
        "status": result.status,
        "upper_bound_log": certificate.upper_bound_log if certificate else None,
        "lower_bound_log": certificate.lower_bound_log if certificate else None,
        "factor": certificate.overhead_factor_bound if certificate else None,
        "certificate_kind": certificate.certificate_kind if certificate else None,
        "formal_numerical_proof": certificate.formal_numerical_proof if certificate else None,
        "expanded_nodes": result.expanded_nodes,
        "profile": result.profile.__dict__ if result.profile else None,
    }


def _record(family: str, n: int, seed: int, deadline_s: float, checkpoints: tuple[float, ...]) -> dict[str, object]:
    circuit = make_heterogeneous_qpd_circuit(family, n, seed)
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    incumbent = warm_start_partition(graph, qmax=n // 2, exact_num_fragments=True, variant="h2")
    certicut = tuple(_certicut_snapshot(graph, n, checkpoint) for checkpoint in checkpoints)
    scip = {
        variant: solve_scip_core(
            graph, variant=variant, time_limit_s=deadline_s,
            incumbent_partition=incumbent[0] if incumbent else None,
            checkpoint_times_s=checkpoints,
        ).as_dict()
        for variant in ("g0_basic", "g1_cardinality", "g2_b2s")
    }
    return {
        "experiment": "E7_heterogeneous_qpd_scaling_matched",
        "family": family,
        "num_qubits": n,
        "seed": seed,
        "cost_model": "qiskit_qpd_0.10.0_independent",
        "thread_limit": 1,
        "requested_deadline_s": deadline_s,
        "checkpoints_s": checkpoints,
        "certicut_checkpoints": certicut,
        "scip": scip,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", type=int, nargs="+", default=(20, 24, 32, 40))
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--deadline-s", type=float, default=60.0)
    parser.add_argument("--checkpoints-s", type=float, nargs="+", default=(2.0, 10.0, 60.0))
    parser.add_argument("--output", type=Path, default=Path("results/phase12_e7_heterogeneous_scaling.jsonl"))
    args = parser.parse_args()
    if any(n < 4 or n % 2 for n in args.sizes):
        raise ValueError("sizes must be even and at least four")
    checkpoints = tuple(value for value in args.checkpoints_s if value <= args.deadline_s)
    completed = set()
    if args.output.exists():
        completed = {(row["family"], row["num_qubits"], row["seed"]) for row in map(json.loads, args.output.read_text(encoding="utf-8").splitlines())}
    with args.output.open("a", encoding="utf-8") as stream:
        for family in FAMILIES:
            for n in args.sizes:
                for seed in range(args.seeds):
                    key = (family, n, seed)
                    if key in completed:
                        continue
                    stream.write(json.dumps(_record(family, n, seed, args.deadline_s, checkpoints)) + "\n")
                    stream.flush()


if __name__ == "__main__":
    main()
