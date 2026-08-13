"""Track A deterministic benchmark runner with failure-safe JSONL records."""

from __future__ import annotations

import os
import psutil
from time import perf_counter

from certicut.baselines.graph_heuristics import solve_graph_heuristic
from certicut.baselines.kahip import solve_kahip
from certicut.benchmark.instance import BenchmarkInstance
from certicut.benchmark.schema import BenchmarkRecord
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def run_track_a(instance: BenchmarkInstance, method: str, *, node_limit: int | None = None) -> BenchmarkRecord:
    """Run one method; preserve failures as records instead of dropping data."""
    process = psutil.Process(os.getpid())
    before = process.memory_info().rss
    started = perf_counter()
    try:
        graph = build_interaction_graph(instance.circuit())
        if method in {"h2", "h3"}:
            result = solve_graph_heuristic(graph, qmax=instance.qmax, variant=method)
            return _record(instance, method, result.status, result.runtime_s, result.objective_log_cost, None, None, None, None, None, len(result.cut_instruction_indices), result.fragment_sizes, None, None, None, before)
        if method in {"kahip_fast", "kahip_eco", "kahip_strong"}:
            result = solve_kahip(graph, seed=instance.seed, mode=method.removeprefix("kahip_"))
            return _record(instance, method, result.status, result.runtime_s, result.objective_log_cost, None, None, None, None, None, len(result.cut_instruction_indices), result.fragment_sizes, None, None, None, before)
        if method in {"a0_b0_h0", "a1_b0_h2", "a2_b2s_h0", "certicut_b2s_h2"}:
            lp_variant, warm_start = {
                "a0_b0_h0": ("b0", "h0"),
                "a1_b0_h2": ("b0", "h2"),
                "a2_b2s_h0": ("b2s_root", "h0"),
                "certicut_b2s_h2": ("b2s_root", "h2"),
            }[method]
            result = solve_certified_bnb(graph, qmax=instance.qmax, exact_num_fragments=True, node_limit=node_limit, lp_variant=lp_variant, warm_start_variant=warm_start, collect_profile=True)
            certificate = result.certificate
            profile = result.profile
            return _record(instance, method, result.status, perf_counter() - started, certificate.upper_bound_log if certificate else None, certificate.lower_bound_log if certificate else None, certificate.additive_log_gap if certificate else None, certificate.overhead_factor_bound if certificate else None, certificate.bound_closed if certificate else None, certificate.proven_optimal if certificate else None, len(result.cut_instruction_indices), tuple(map(len, result.fragments)), result.expanded_nodes, profile.root_separation_time_s if profile else None, profile.node_lp_time_total_s if profile else None, before)
        if method == "phase2_milp":
            result = solve_exact_partition(graph, num_fragments=2, qmax=instance.qmax, exact_num_fragments=True)
            return _record(instance, method, result.status, perf_counter() - started, result.objective_log_cost, result.objective_log_cost, 0.0 if result.status == "optimal" else None, 1.0 if result.status == "optimal" else None, result.status == "optimal", result.status == "optimal", len(result.cut_instruction_indices), tuple(map(len, result.fragments)), None, None, None, before)
        raise ValueError(f"unknown Track A method '{method}'")
    except Exception as error:
        return BenchmarkRecord(instance.instance_id, method, instance.track, "error", perf_counter() - started, None, None, None, None, None, None, None, None, None, None, None, _peak_mb(before), repr(error))


def record_certicut_result(instance: BenchmarkInstance, result, runtime_s: float) -> BenchmarkRecord:
    """Serialize a precomputed CertiCut trajectory without re-running B&B."""
    certificate = result.certificate
    profile = result.profile
    return BenchmarkRecord(
        instance.instance_id, "certicut_b2s_h2", instance.track, result.status, runtime_s,
        certificate.upper_bound_log if certificate else None, None,
        certificate.lower_bound_log if certificate else None,
        certificate.upper_bound_log if certificate else None,
        certificate.additive_log_gap if certificate else None,
        certificate.overhead_factor_bound if certificate else None,
        certificate.bound_closed if certificate else None,
        certificate.proven_optimal if certificate else None,
        len(result.cut_instruction_indices), tuple(map(len, result.fragments)), result.expanded_nodes,
        profile.root_separation_time_s if profile else None,
        profile.node_lp_time_total_s if profile else None, None,
    )


def _record(instance, method, status, runtime, objective, lb, gap, factor, bound_closed, optimal, cuts, sizes, nodes, root_time, tree_time, before):
    return BenchmarkRecord(instance.instance_id, method, instance.track, status, runtime, objective, None, lb, objective, gap, factor, bound_closed, optimal, cuts, sizes, nodes, root_time, tree_time, _peak_mb(before))


def _peak_mb(before: int) -> float:
    return max(0.0, (psutil.Process(os.getpid()).memory_info().rss - before) / 1_000_000)
