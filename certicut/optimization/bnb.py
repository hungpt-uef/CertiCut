"""Certified anytime vanilla Branch-and-Bound for two-fragment CertiCut V1."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
from math import exp
from time import monotonic, perf_counter
from typing import Any

from certicut.graph.interaction import InteractionGraph, graph_partition_objective
from certicut.optimization.certificate import Certificate, make_certificate
from certicut.optimization.heuristics import warm_start_partition
from certicut.optimization.lp import LPRelaxationResult, LPVariant, solve_b2_separated_lp, solve_b2_with_cut_pool, solve_lp_variant


_TOLERANCE = 1e-9


@dataclass(frozen=True)
class BnBTimelineEvent:
    expanded_nodes: int
    open_nodes: int
    node_depth: int | None
    node_lb: float | None
    global_lb: float | None
    incumbent_ub: float | None
    additive_log_gap: float | None
    overhead_factor_bound: float | None
    event: str
    elapsed_s: float


@dataclass(frozen=True)
class BnBResult:
    status: str
    partition: tuple[int, ...] | None
    fragments: tuple[tuple[int, ...], ...]
    cut_edges: tuple[tuple[int, int], ...]
    cut_instruction_indices: tuple[int, ...]
    certificate: Certificate | None
    expanded_nodes: int
    timeline: tuple[BnBTimelineEvent, ...]
    profile: "BnBProfile | None" = None
    strong_branching_states: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _Node:
    fixed_assignments: tuple[tuple[int, int], ...]
    lower_bound: float
    assignments: tuple[tuple[float, float], ...]
    pool_version: int = 0


@dataclass
class GlobalCutPool:
    """Monotonic set of globally valid triangle facets."""

    cuts: set[tuple[int, int, int, int]]
    version: int = 0

    def add(self, new_cuts: tuple[tuple[int, int, int, int], ...]) -> int:
        before = len(self.cuts)
        self.cuts.update(new_cuts)
        added = len(self.cuts) - before
        if added:
            self.version += 1
        return added


@dataclass(frozen=True)
class BnBProfile:
    root_lp_lb: float
    initial_ub: float
    root_gap_log: float
    root_factor_bound: float
    root_lp_variable_count: int
    root_lp_constraint_count: int
    generated_nodes: int
    pruned_by_bound: int
    pruned_infeasible: int
    integral_lp_nodes: int
    max_frontier_size: int
    lp_solve_count: int
    lp_time_total_s: float
    warm_start_time_s: float
    time_to_best_ub_s: float
    solve_time_s: float
    root_separation_rounds: int = 0
    root_cuts_added: int = 0
    root_separation_time_s: float = 0.0
    node_lp_solve_count: int = 0
    node_lp_time_total_s: float = 0.0
    cuts_discovered_nodes: int = 0
    node_separation_rounds: int = 0
    node_separation_lp_solves: int = 0
    node_separation_time_s: float = 0.0
    stale_nodes_popped: int = 0
    stale_nodes_reoptimized: int = 0
    reoptimization_bound_gain_total: float = 0.0
    pool_version_final: int = 0
    sb_calls: int = 0
    sb_candidates_probed: int = 0
    sb_probe_lp_solves: int = 0
    sb_probe_time_s: float = 0.0
    sb_selected_probe_reuse_count: int = 0


@dataclass
class _ProfileAccumulator:
    root_lp_lb: float = 0.0
    initial_ub: float = 0.0
    root_lp_variable_count: int = 0
    root_lp_constraint_count: int = 0
    generated_nodes: int = 0
    pruned_by_bound: int = 0
    pruned_infeasible: int = 0
    integral_lp_nodes: int = 0
    max_frontier_size: int = 0
    lp_solve_count: int = 0
    lp_time_total_s: float = 0.0
    warm_start_time_s: float = 0.0
    time_to_best_ub_s: float = 0.0
    root_separation_rounds: int = 0
    root_cuts_added: int = 0
    root_separation_time_s: float = 0.0
    node_lp_solve_count: int = 0
    node_lp_time_total_s: float = 0.0
    cuts_discovered_nodes: int = 0
    node_separation_rounds: int = 0
    node_separation_lp_solves: int = 0
    node_separation_time_s: float = 0.0
    stale_nodes_popped: int = 0
    stale_nodes_reoptimized: int = 0
    reoptimization_bound_gain_total: float = 0.0
    pool_version_final: int = 0
    sb_calls: int = 0
    sb_candidates_probed: int = 0
    sb_probe_lp_solves: int = 0
    sb_probe_time_s: float = 0.0
    sb_selected_probe_reuse_count: int = 0


def solve_certified_bnb(
    graph: InteractionGraph,
    *,
    qmax: int,
    exact_num_fragments: bool = True,
    node_limit: int | None = None,
    time_limit_s: float | None = None,
    collect_profile: bool = False,
    lp_variant: LPVariant = "b0",
    node_separation_top_k: int = 100,
    node_separation_max_rounds: int = 3,
    node_separation_depth_limit: int | None = None,
    warm_start_variant: str = "h0",
    branching_rule: str = "mf",
    strong_branching_k: int | None = None,
    collect_strong_branching_states: bool = False,
) -> BnBResult:
    """Run safe-checkpoint best-bound B&B; K=2 only in Phase 3A."""
    if qmax < 1:
        raise ValueError("qmax must be positive")
    if node_limit is not None and node_limit < 0:
        raise ValueError("node_limit must be non-negative")
    if time_limit_s is not None and time_limit_s < 0:
        raise ValueError("time_limit_s must be non-negative")
    if graph.num_qubits > 2 * qmax:
        return _infeasible_result()

    start = perf_counter()
    profile = _ProfileAccumulator() if collect_profile else None
    warm_started = perf_counter()
    initial = warm_start_partition(
        graph, qmax=qmax, exact_num_fragments=exact_num_fragments, variant=warm_start_variant
    )
    if profile:
        profile.warm_start_time_s = perf_counter() - warm_started
    if initial is None:
        return _infeasible_result()
    incumbent_partition, incumbent_ub = initial
    if profile:
        profile.initial_ub = incumbent_ub
        profile.time_to_best_ub_s = perf_counter() - start
    lp_started = perf_counter()
    pool = GlobalCutPool(set())
    if lp_variant in ("b2s_root", "b2s_node"):
        remaining = max(0.0, time_limit_s - (perf_counter() - start)) if time_limit_s is not None else None
        separated = solve_b2_separated_lp(
            graph, qmax=qmax, exact_num_fragments=exact_num_fragments, deadline_s=remaining
        )
        root_lp = separated.relaxation
        pool.add(separated.active_cuts)
        if profile:
            profile.root_separation_rounds = separated.separation_rounds
            profile.root_cuts_added = separated.triangles_added
            profile.root_separation_time_s = separated.lp_time_total_s + separated.matrix_build_time_s
    else:
        root_lp = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=exact_num_fragments, variant=lp_variant)
    if profile:
        profile.lp_solve_count += 1
        profile.lp_time_total_s += perf_counter() - lp_started
    if root_lp.status == "infeasible":
        return _infeasible_result()
    root = _node_from_lp((), root_lp, pool.version)
    if profile:
        profile.root_lp_lb = root.lower_bound
        profile.root_lp_variable_count = root_lp.variable_count
        profile.root_lp_constraint_count = root_lp.constraint_count
    frontier: list[tuple[float, int, int, _Node]] = [(root.lower_bound, 0, 0, root)]
    if profile:
        profile.max_frontier_size = 1
    sequence = 1
    expanded = 0
    timeline: list[BnBTimelineEvent] = []
    strong_branching_states: list[dict[str, Any]] = []
    _append_timeline(timeline, "root", 0, frontier, root, incumbent_ub, perf_counter() - start)
    if time_limit_s is not None and perf_counter() - start >= time_limit_s:
        if profile:
            profile.pool_version_final = pool.version
        return _limited_result("time_limit", graph, frontier, incumbent_partition, incumbent_ub, expanded, timeline, profile, start)

    while frontier:
        if node_limit is not None and expanded >= node_limit:
            if profile:
                profile.pool_version_final = pool.version
            return _limited_result("node_limit", graph, frontier, incumbent_partition, incumbent_ub, expanded, timeline, profile, start)
        if time_limit_s is not None and perf_counter() - start >= time_limit_s:
            if profile:
                profile.pool_version_final = pool.version
            return _limited_result("time_limit", graph, frontier, incumbent_partition, incumbent_ub, expanded, timeline, profile, start)

        _, _, _, node = heapq.heappop(frontier)
        if lp_variant == "b2s_node" and node.pool_version < pool.version:
            if profile:
                profile.stale_nodes_popped += 1
            stale_bound = node.lower_bound
            if node_separation_depth_limit is None or len(node.fixed_assignments) <= node_separation_depth_limit:
                refreshed = solve_b2_separated_lp(
                    graph, qmax=qmax, exact_num_fragments=exact_num_fragments,
                    fixed_assignments=dict(node.fixed_assignments), initial_cuts=tuple(sorted(pool.cuts)),
                    policy="top_k", top_k=node_separation_top_k, max_rounds=node_separation_max_rounds,
                )
                added = pool.add(refreshed.active_cuts)
                refreshed_lp = refreshed.relaxation
                separation_rounds = refreshed.separation_rounds
                separation_solves = refreshed.lp_solve_count
                separation_time = refreshed.lp_time_total_s + refreshed.matrix_build_time_s
            else:
                refreshed_lp = solve_b2_with_cut_pool(
                    graph, qmax=qmax, exact_num_fragments=exact_num_fragments,
                    fixed_assignments=dict(node.fixed_assignments), cuts=tuple(sorted(pool.cuts)),
                )
                added = separation_rounds = separation_solves = 0
                separation_time = 0.0
            node = _node_from_lp(node.fixed_assignments, refreshed_lp, pool.version)
            if profile:
                profile.stale_nodes_reoptimized += 1
                profile.reoptimization_bound_gain_total += max(0.0, node.lower_bound - stale_bound)
                profile.cuts_discovered_nodes += added
                profile.node_separation_rounds += separation_rounds
                profile.node_separation_lp_solves += separation_solves
                profile.node_separation_time_s += separation_time
        event = "prune"
        if node.lower_bound < incumbent_ub - _TOLERANCE:
            partition = _integral_partition(node.assignments)
            if partition is not None:
                objective = graph_partition_objective(graph, partition)
                if objective < incumbent_ub - _TOLERANCE:
                    incumbent_partition, incumbent_ub = partition, objective
                    if profile:
                        profile.time_to_best_ub_s = perf_counter() - start
                    event = "incumbent"
                else:
                    if profile:
                        profile.integral_lp_nodes += 1
                    event = "integral"
            else:
                cached_children: dict[int, LPRelaxationResult] = {}
                if branching_rule == "mf":
                    branch_qubit = _most_fractional_qubit(node.assignments, dict(node.fixed_assignments))
                elif branching_rule == "strong":
                    branch_qubit, cached_children, state = _strong_branch(
                        graph, node, qmax, exact_num_fragments, tuple(sorted(pool.cuts)), strong_branching_k
                    )
                    if profile:
                        profile.sb_calls += 1
                        profile.sb_candidates_probed += len(state["candidate_scores"])
                        profile.sb_probe_lp_solves += 2 * len(state["candidate_scores"])
                        profile.sb_probe_time_s += state["probe_time_s"]
                        profile.sb_selected_probe_reuse_count += 2
                    if collect_strong_branching_states:
                        strong_branching_states.append(state)
                else:
                    raise ValueError(f"unknown branching rule '{branching_rule}'")
                for fragment in (0, 1):
                    fixed = (*node.fixed_assignments, (branch_qubit, fragment))
                    lp_started = perf_counter()
                    if fragment in cached_children:
                        child_lp = cached_children[fragment]
                    elif lp_variant == "b2s_root":
                        child_lp = solve_b2_with_cut_pool(
                            graph, qmax=qmax, exact_num_fragments=exact_num_fragments,
                            fixed_assignments=dict(fixed), cuts=tuple(sorted(pool.cuts)),
                        )
                    elif lp_variant == "b2s_node" and (node_separation_depth_limit is None or len(fixed) <= node_separation_depth_limit):
                        separated = solve_b2_separated_lp(
                            graph, qmax=qmax, exact_num_fragments=exact_num_fragments,
                            fixed_assignments=dict(fixed), initial_cuts=tuple(sorted(pool.cuts)),
                            policy="top_k", top_k=node_separation_top_k, max_rounds=node_separation_max_rounds,
                        )
                        child_lp = separated.relaxation
                        added = pool.add(separated.active_cuts)
                        if profile:
                            profile.cuts_discovered_nodes += added
                            profile.node_separation_rounds += separated.separation_rounds
                            profile.node_separation_lp_solves += separated.lp_solve_count
                            profile.node_separation_time_s += separated.lp_time_total_s + separated.matrix_build_time_s
                    else:
                        child_lp = solve_b2_with_cut_pool(
                            graph, qmax=qmax, exact_num_fragments=exact_num_fragments,
                            fixed_assignments=dict(fixed), cuts=tuple(sorted(pool.cuts)),
                        )
                    if profile:
                        profile.generated_nodes += 1
                        if fragment not in cached_children:
                            elapsed = perf_counter() - lp_started
                            profile.lp_solve_count += 1
                            profile.lp_time_total_s += elapsed
                            profile.node_lp_solve_count += 1
                            profile.node_lp_time_total_s += elapsed
                    if child_lp.status == "optimal" and child_lp.lower_bound_log is not None:
                        child = _node_from_lp(fixed, child_lp, pool.version)
                        if child.lower_bound < incumbent_ub - _TOLERANCE:
                            heapq.heappush(frontier, (child.lower_bound, len(fixed), sequence, child))
                            sequence += 1
                        elif profile:
                            profile.pruned_by_bound += 1
                    elif profile:
                        profile.pruned_infeasible += 1
                event = "branch"
            if profile:
                profile.max_frontier_size = max(profile.max_frontier_size, len(frontier))
        elif profile:
            profile.pruned_by_bound += 1
        expanded += 1
        _append_timeline(timeline, event, expanded, frontier, node, incumbent_ub, perf_counter() - start)

    certificate = make_certificate(
        incumbent_ub, incumbent_ub, tolerance=_TOLERANCE,
        numerical_safety_margin_log=_TOLERANCE, certificate_kind="solver_tolerance",
    )
    if profile:
        profile.pool_version_final = pool.version
    return _result("optimal", graph, incumbent_partition, certificate, expanded, timeline, _finalize_profile(profile, incumbent_ub, start), strong_branching_states)


def _node_from_lp(
    fixed_assignments: tuple[tuple[int, int], ...], result: LPRelaxationResult, pool_version: int = 0
) -> _Node:
    assert result.lower_bound_log is not None and result.assignments is not None
    return _Node(fixed_assignments, result.lower_bound_log, result.assignments, pool_version)


def _integral_partition(assignments: tuple[tuple[float, float], ...]) -> tuple[int, ...] | None:
    labels = []
    for first, second in assignments:
        if abs(first - 1.0) <= _TOLERANCE and abs(second) <= _TOLERANCE:
            labels.append(0)
        elif abs(second - 1.0) <= _TOLERANCE and abs(first) <= _TOLERANCE:
            labels.append(1)
        else:
            return None
    return tuple(labels)


def _most_fractional_qubit(
    assignments: tuple[tuple[float, float], ...], fixed: dict[int, int]
) -> int:
    candidates = [
        (abs(first - 0.5), qubit)
        for qubit, (first, _) in enumerate(assignments)
        if qubit != 0 and qubit not in fixed
    ]
    if not candidates:
        raise RuntimeError("fractional LP node has no unfixed qubit")
    return min(candidates)[1]


def _strong_branch(
    graph: InteractionGraph, node: _Node, qmax: int, exact_num_fragments: bool,
    root_cuts: tuple[tuple[int, int, int, int], ...], candidate_limit: int | None,
) -> tuple[int, dict[int, LPRelaxationResult], dict[str, Any]]:
    """Probe candidate assignments using the exact frozen B2S-R node relaxation."""
    candidates = sorted(
        ((abs(first - 0.5), qubit) for qubit, (first, _) in enumerate(node.assignments) if qubit != 0 and qubit not in dict(node.fixed_assignments)),
        key=lambda value: (value[0], value[1]),
    )
    if candidate_limit is not None:
        candidates = candidates[:candidate_limit]
    if not candidates:
        raise RuntimeError("strong branching requires an unfixed fractional candidate")
    started = perf_counter()
    probes: dict[int, tuple[LPRelaxationResult, LPRelaxationResult]] = {}
    scores: dict[str, float] = {}
    for _, qubit in candidates:
        children = []
        for fragment in (0, 1):
            fixed = (*node.fixed_assignments, (qubit, fragment))
            children.append(solve_b2_with_cut_pool(
                graph, qmax=qmax, exact_num_fragments=exact_num_fragments,
                fixed_assignments=dict(fixed), cuts=root_cuts,
            ))
        probes[qubit] = (children[0], children[1])
        improvements = [
            (child.lower_bound_log - node.lower_bound) if child.status == "optimal" and child.lower_bound_log is not None else 1e12
            for child in children
        ]
        scores[str(qubit)] = 0.9 * min(improvements) + 0.1 * max(improvements)
    selected = max((score, -qubit, qubit) for qubit, score in ((int(key), value) for key, value in scores.items()))[2]
    selected_children = {0: probes[selected][0], 1: probes[selected][1]}
    state = {
        "node_depth": len(node.fixed_assignments),
        "current_lb": node.lower_bound,
        "fractional_variables": [qubit for _, qubit in candidates],
        "candidate_scores": scores,
        "selected_variable": selected,
        "probe_time_s": perf_counter() - started,
    }
    return selected, selected_children, state


def _global_lower_bound(frontier: list[tuple[float, int, int, _Node]], incumbent_ub: float) -> float:
    # The incumbent is a resolved feasible region, so global OPT cannot exceed it.
    return min(incumbent_ub, min((item[0] for item in frontier), default=incumbent_ub))


def _append_timeline(
    timeline: list[BnBTimelineEvent],
    event: str,
    expanded: int,
    frontier: list[tuple[float, int, int, _Node]],
    node: _Node | None,
    incumbent_ub: float,
    elapsed_s: float,
) -> None:
    global_lb = _global_lower_bound(frontier, incumbent_ub)
    certificate = make_certificate(
        global_lb, incumbent_ub, tolerance=_TOLERANCE,
        numerical_safety_margin_log=_TOLERANCE, certificate_kind="solver_tolerance",
    )
    timeline.append(
        BnBTimelineEvent(
            expanded_nodes=expanded,
            open_nodes=len(frontier),
            node_depth=len(node.fixed_assignments) if node else None,
            node_lb=node.lower_bound if node else None,
            global_lb=global_lb,
            incumbent_ub=incumbent_ub,
            additive_log_gap=certificate.additive_log_gap,
            overhead_factor_bound=certificate.overhead_factor_bound,
            event=event,
            elapsed_s=elapsed_s,
        )
    )


def _limited_result(
    status: str,
    graph: InteractionGraph,
    frontier: list[tuple[float, int, int, _Node]],
    partition: tuple[int, ...],
    incumbent_ub: float,
    expanded: int,
    timeline: list[BnBTimelineEvent],
    profile: _ProfileAccumulator | None,
    start: float,
) -> BnBResult:
    lower_bound = _global_lower_bound(frontier, incumbent_ub)
    certificate = make_certificate(
        lower_bound, incumbent_ub, tolerance=_TOLERANCE,
        numerical_safety_margin_log=_TOLERANCE, certificate_kind="solver_tolerance",
    )
    _append_timeline(timeline, status, expanded, frontier, None, incumbent_ub, perf_counter() - start)
    return _result(status, graph, partition, certificate, expanded, timeline, _finalize_profile(profile, incumbent_ub, start))


def _result(
    status: str,
    graph: InteractionGraph,
    partition: tuple[int, ...],
    certificate: Certificate,
    expanded: int,
    timeline: list[BnBTimelineEvent],
    profile: BnBProfile | None = None,
    strong_branching_states: list[dict[str, Any]] | None = None,
) -> BnBResult:
    return BnBResult(
        status=status,
        partition=partition,
        fragments=tuple(
            tuple(qubit for qubit, label in enumerate(partition) if label == fragment)
            for fragment in (0, 1)
        ),
        cut_edges=tuple(
            (edge.u, edge.v) for edge in graph.edges if partition[edge.u] != partition[edge.v]
        ),
        cut_instruction_indices=tuple(
            instruction_index
            for edge in graph.edges
            if partition[edge.u] != partition[edge.v]
            for instruction_index in edge.instruction_indices
        ),
        certificate=certificate,
        expanded_nodes=expanded,
        timeline=tuple(timeline),
        profile=profile,
        strong_branching_states=tuple(strong_branching_states or ()),
    )


def _infeasible_result() -> BnBResult:
    return BnBResult("infeasible", None, (), (), (), None, 0, ())


def _finalize_profile(
    profile: _ProfileAccumulator | None, incumbent_ub: float, start: float
) -> BnBProfile | None:
    if profile is None:
        return None
    root_gap = max(0.0, profile.initial_ub - profile.root_lp_lb)
    return BnBProfile(
        root_lp_lb=profile.root_lp_lb,
        initial_ub=profile.initial_ub,
        root_gap_log=root_gap,
        root_factor_bound=exp(root_gap),
        root_lp_variable_count=profile.root_lp_variable_count,
        root_lp_constraint_count=profile.root_lp_constraint_count,
        generated_nodes=profile.generated_nodes,
        pruned_by_bound=profile.pruned_by_bound,
        pruned_infeasible=profile.pruned_infeasible,
        integral_lp_nodes=profile.integral_lp_nodes,
        max_frontier_size=profile.max_frontier_size,
        lp_solve_count=profile.lp_solve_count,
        lp_time_total_s=profile.lp_time_total_s,
        warm_start_time_s=profile.warm_start_time_s,
        time_to_best_ub_s=profile.time_to_best_ub_s,
        solve_time_s=perf_counter() - start,
        root_separation_rounds=profile.root_separation_rounds,
        root_cuts_added=profile.root_cuts_added,
        root_separation_time_s=profile.root_separation_time_s,
        node_lp_solve_count=profile.node_lp_solve_count,
        node_lp_time_total_s=profile.node_lp_time_total_s,
        cuts_discovered_nodes=profile.cuts_discovered_nodes,
        node_separation_rounds=profile.node_separation_rounds,
        node_separation_lp_solves=profile.node_separation_lp_solves,
        node_separation_time_s=profile.node_separation_time_s,
        stale_nodes_popped=profile.stale_nodes_popped,
        stale_nodes_reoptimized=profile.stale_nodes_reoptimized,
        reoptimization_bound_gain_total=profile.reoptimization_bound_gain_total,
        pool_version_final=profile.pool_version_final,
        sb_calls=profile.sb_calls,
        sb_candidates_probed=profile.sb_candidates_probed,
        sb_probe_lp_solves=profile.sb_probe_lp_solves,
        sb_probe_time_s=profile.sb_probe_time_s,
        sb_selected_probe_reuse_count=profile.sb_selected_probe_reuse_count,
    )
