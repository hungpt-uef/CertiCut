"""LP relaxation used as a valid lower-bound oracle for Branch-and-Bound."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from time import perf_counter
from typing import Literal, Mapping

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from certicut.graph.interaction import InteractionGraph


@dataclass(frozen=True)
class LPRelaxationResult:
    status: str
    lower_bound_log: float | None
    assignments: tuple[tuple[float, float], ...] | None
    variable_count: int = 0
    constraint_count: int = 0
    cut_values: dict[tuple[int, int], float] | None = None
    fractional_variable_count: int = 0
    max_fractionality: float = 0.0


@dataclass(frozen=True)
class SeparatedLPResult:
    relaxation: LPRelaxationResult
    separation_rounds: int
    triangles_added: int
    lp_solve_count: int
    lp_time_total_s: float
    matrix_build_time_s: float
    active_cuts: tuple[tuple[int, int, int, int], ...]
    stopped_by_time: bool = False


def solve_lp_relaxation(
    graph: InteractionGraph,
    *,
    qmax: int,
    exact_num_fragments: bool,
    fixed_assignments: Mapping[int, int] | None = None,
) -> LPRelaxationResult:
    """Solve the K=2 relaxation of the Phase 2 formulation."""
    if qmax < 1:
        raise ValueError("qmax must be positive")
    if graph.num_qubits > 2 * qmax:
        return LPRelaxationResult("infeasible", None, None)
    fixed = {0: 0, **(fixed_assignments or {})}
    if any(qubit < 0 or qubit >= graph.num_qubits for qubit in fixed):
        raise ValueError("fixed assignment qubit out of range")
    if any(fragment not in (0, 1) for fragment in fixed.values()):
        raise ValueError("Phase 3A supports only two fragments")
    if fixed.get(0) != 0:
        return LPRelaxationResult("infeasible", None, None)

    n = graph.num_qubits
    variable_count = 2 * n + len(graph.edges)
    costs = np.zeros(variable_count)
    costs[2 * n :] = [edge.qpd_log_cost for edge in graph.edges]
    equality = lil_matrix((n, variable_count), dtype=float)
    equality_rhs = np.ones(n)
    for qubit in range(n):
        equality[qubit, _assignment_index(qubit, 0)] = 1
        equality[qubit, _assignment_index(qubit, 1)] = 1

    inequality_count = 2 + (2 if exact_num_fragments else 0) + 4 * len(graph.edges)
    inequality = lil_matrix((inequality_count, variable_count), dtype=float)
    inequality_rhs = np.zeros(inequality_count)
    row = 0
    for fragment in range(2):
        for qubit in range(n):
            inequality[row, _assignment_index(qubit, fragment)] = 1
        inequality_rhs[row] = qmax
        row += 1
    if exact_num_fragments:
        for fragment in range(2):
            for qubit in range(n):
                inequality[row, _assignment_index(qubit, fragment)] = -1
            inequality_rhs[row] = -1
            row += 1
    for edge_index, edge in enumerate(graph.edges):
        x_index = 2 * n + edge_index
        for fragment in range(2):
            inequality[row, x_index] = -1
            inequality[row, _assignment_index(edge.u, fragment)] = 1
            inequality[row, _assignment_index(edge.v, fragment)] = -1
            row += 1
            inequality[row, x_index] = -1
            inequality[row, _assignment_index(edge.u, fragment)] = -1
            inequality[row, _assignment_index(edge.v, fragment)] = 1
            row += 1

    bounds = [(0.0, 1.0)] * variable_count
    for qubit, fragment in fixed.items():
        bounds[_assignment_index(qubit, fragment)] = (1.0, 1.0)
        bounds[_assignment_index(qubit, 1 - fragment)] = (0.0, 0.0)
    result = linprog(
        costs,
        A_ub=inequality.tocsr(),
        b_ub=inequality_rhs,
        A_eq=equality.tocsr(),
        b_eq=equality_rhs,
        bounds=bounds,
        method="highs",
    )
    if result.status == 2:
        return LPRelaxationResult("infeasible", None, None)
    if result.status != 0 or result.x is None:
        raise RuntimeError(f"HiGHS LP failed: status={result.status}, message={result.message}")
    assignments = tuple(
        (float(result.x[_assignment_index(qubit, 0)]), float(result.x[_assignment_index(qubit, 1)]))
        for qubit in range(n)
    )
    return LPRelaxationResult("optimal", float(result.fun), assignments, variable_count, n + inequality_count)


LPVariant = Literal["b0", "b1_compact", "b2_metric", "b2s_root", "b2s_node"]


def solve_lp_variant(
    graph: InteractionGraph, *, qmax: int, exact_num_fragments: bool,
    fixed_assignments: Mapping[int, int] | None = None, variant: LPVariant = "b0"
) -> LPRelaxationResult:
    """Dispatch B0 assignment, B1 compact, or B2 metric relaxation."""
    if variant == "b0":
        return solve_lp_relaxation(graph, qmax=qmax, exact_num_fragments=exact_num_fragments, fixed_assignments=fixed_assignments)
    if variant == "b1_compact":
        return _solve_z_lp(graph, qmax, exact_num_fragments, fixed_assignments, metric=False)
    if variant == "b2_metric":
        return _solve_z_lp(graph, qmax, exact_num_fragments, fixed_assignments, metric=True)
    if variant in ("b2s_root", "b2s_node"):
        raise ValueError(f"{variant} is orchestrated by solve_certified_bnb")
    raise ValueError(f"unknown LP variant '{variant}'")


def _solve_z_lp(
    graph: InteractionGraph, qmax: int, exact_num_fragments: bool,
    fixed_assignments: Mapping[int, int] | None, metric: bool,
) -> LPRelaxationResult:
    n = graph.num_qubits
    if qmax < 1 or n > 2 * qmax:
        return LPRelaxationResult("infeasible", None, None)
    if metric and (not exact_num_fragments or qmax != (n + 1) // 2):
        raise ValueError("B2 metric relaxation requires exact balanced K=2 capacity")
    fixed = {0: 0, **(fixed_assignments or {})}
    if fixed.get(0) != 0 or any(q < 0 or q >= n or f not in (0, 1) for q, f in fixed.items()):
        return LPRelaxationResult("infeasible", None, None)
    pairs = list(combinations(range(n), 2)) if metric else [(edge.u, edge.v) for edge in graph.edges]
    pair_index = {pair: n + index for index, pair in enumerate(pairs)}
    variable_count = n + len(pairs)
    costs = np.zeros(variable_count)
    for edge in graph.edges:
        costs[pair_index[(edge.u, edge.v)]] = edge.qpd_log_cost
    # Two XOR lower constraints per pair, optional two upper constraints, four triangle facets.
    inequality_count = 2 + 2 * len(pairs) + (2 * len(pairs) if metric else 0) + (4 * (n * (n - 1) * (n - 2) // 6) if metric else 0)
    inequality = lil_matrix((inequality_count, variable_count), dtype=float)
    rhs = np.zeros(inequality_count)
    row = 0
    for sign, bound in ((1, qmax), (-1, -(n - qmax))):
        for qubit in range(n):
            inequality[row, qubit] = sign
        rhs[row] = bound
        row += 1
    for u, v in pairs:
        x = pair_index[(u, v)]
        inequality[row, u], inequality[row, v], inequality[row, x] = 1, -1, -1; row += 1
        inequality[row, u], inequality[row, v], inequality[row, x] = -1, 1, -1; row += 1
        if metric:
            inequality[row, u], inequality[row, v], inequality[row, x] = -1, -1, 1; row += 1
            inequality[row, u], inequality[row, v], inequality[row, x] = 1, 1, 1; rhs[row] = 2; row += 1
    if metric:
        for i, j, k in combinations(range(n), 3):
            ij, ik, jk = pair_index[(i, j)], pair_index[(i, k)], pair_index[(j, k)]
            for left, right_a, right_b in ((ij, ik, jk), (ik, ij, jk), (jk, ij, ik)):
                inequality[row, left], inequality[row, right_a], inequality[row, right_b] = 1, -1, -1; row += 1
            inequality[row, ij], inequality[row, ik], inequality[row, jk] = 1, 1, 1; rhs[row] = 2; row += 1
    equal_rows = 1 if metric else 0
    equality = lil_matrix((equal_rows, variable_count), dtype=float)
    equality_rhs = np.zeros(equal_rows)
    if metric:
        for pair in pairs:
            equality[0, pair_index[pair]] = 1
        equality_rhs[0] = (n // 2) * ((n + 1) // 2)
    bounds = [(0.0, 1.0)] * variable_count
    for qubit, fragment in fixed.items():
        bounds[qubit] = (float(fragment), float(fragment))
    result = linprog(costs, A_ub=inequality.tocsr(), b_ub=rhs, A_eq=equality.tocsr() if equal_rows else None, b_eq=equality_rhs if equal_rows else None, bounds=bounds, method="highs")
    if result.status == 2:
        return LPRelaxationResult("infeasible", None, None, variable_count, row + equal_rows)
    if result.status != 0 or result.x is None:
        raise RuntimeError(f"HiGHS LP failed: status={result.status}, message={result.message}")
    assignments = tuple((1.0 - float(result.x[q]), float(result.x[q])) for q in range(n))
    cuts = {pair: float(result.x[pair_index[pair]]) for pair in pairs} if metric else None
    return _with_fractionality(
        LPRelaxationResult("optimal", float(result.fun), assignments, variable_count, row + equal_rows, cuts)
    )


def solve_b2_separated_lp(
    graph: InteractionGraph, *, qmax: int, exact_num_fragments: bool,
    fixed_assignments: Mapping[int, int] | None = None,
    policy: Literal["all_violated", "top_k"] = "all_violated", top_k: int = 100,
    tolerance: float = 1e-9,
    initial_cuts: tuple[tuple[int, int, int, int], ...] = (),
    max_rounds: int | None = None,
    deadline_s: float | None = None,
) -> SeparatedLPResult:
    """Root-only B2 cutting-plane loop with dynamically separated triangles."""
    n = graph.num_qubits
    if not exact_num_fragments or qmax != (n + 1) // 2:
        raise ValueError("B2S requires exact balanced K=2 capacity")
    pairs = list(combinations(range(n), 2))
    pair_index = {pair: n + index for index, pair in enumerate(pairs)}
    active = list(dict.fromkeys(initial_cuts))
    active_set = set(active)
    started = perf_counter()
    lp_time = build_time = 0.0
    solves = 0
    while True:
        result, built, elapsed = _solve_metric_with_triangles(
            graph, qmax, fixed_assignments, pairs, pair_index, active
        )
        build_time += built
        lp_time += elapsed
        solves += 1
        if result.status != "optimal" or result.cut_values is None:
            return SeparatedLPResult(result, solves - 1, len(active), solves, lp_time, build_time, tuple(active), deadline_s is not None and perf_counter() - started >= deadline_s)
        violations = _triangle_violations(result.cut_values, n, tolerance)
        if not violations or (max_rounds is not None and solves - 1 >= max_rounds) or (deadline_s is not None and perf_counter() - started >= deadline_s):
            return SeparatedLPResult(result, solves - 1, len(active), solves, lp_time, build_time, tuple(active), deadline_s is not None and perf_counter() - started >= deadline_s)
        if policy == "top_k":
            violations = violations[:top_k]
        elif policy != "all_violated":
            raise ValueError(f"unknown separation policy '{policy}'")
        new_cuts = [cut for _, cut in violations if cut not in active_set]
        if not new_cuts:
            return SeparatedLPResult(result, solves - 1, len(active), solves, lp_time, build_time, tuple(active))
        active.extend(new_cuts)
        active_set.update(new_cuts)


def solve_b2_with_cut_pool(
    graph: InteractionGraph, *, qmax: int, exact_num_fragments: bool,
    fixed_assignments: Mapping[int, int] | None, cuts: tuple[tuple[int, int, int, int], ...],
) -> LPRelaxationResult:
    """Solve a B2 node using globally valid root triangle cuts without re-separation."""
    if not exact_num_fragments or qmax != (graph.num_qubits + 1) // 2:
        raise ValueError("B2S root pool requires exact balanced K=2 capacity")
    n = graph.num_qubits
    pairs = list(combinations(range(n), 2))
    pair_index = {pair: n + index for index, pair in enumerate(pairs)}
    result, _, _ = _solve_metric_with_triangles(
        graph, qmax, fixed_assignments, pairs, pair_index, list(cuts)
    )
    return result


def _solve_metric_with_triangles(
    graph: InteractionGraph, qmax: int, fixed_assignments: Mapping[int, int] | None,
    pairs: list[tuple[int, int]], pair_index: dict[tuple[int, int], int],
    active: list[tuple[int, int, int, int]],
) -> tuple[LPRelaxationResult, float, float]:
    built_at = perf_counter()
    n = graph.num_qubits
    fixed = {0: 0, **(fixed_assignments or {})}
    if fixed.get(0) != 0 or any(q < 0 or q >= n or f not in (0, 1) for q, f in fixed.items()):
        return LPRelaxationResult("infeasible", None, None), 0.0, 0.0
    variable_count = n + len(pairs)
    costs = np.zeros(variable_count)
    for edge in graph.edges:
        costs[pair_index[(edge.u, edge.v)]] = edge.qpd_log_cost
    inequality = lil_matrix((2 + 4 * len(pairs) + len(active), variable_count), dtype=float)
    rhs = np.zeros(2 + 4 * len(pairs) + len(active))
    row = 0
    for sign, bound in ((1, qmax), (-1, -(n - qmax))):
        for qubit in range(n):
            inequality[row, qubit] = sign
        rhs[row] = bound; row += 1
    for u, v in pairs:
        x = pair_index[(u, v)]
        inequality[row, u], inequality[row, v], inequality[row, x] = 1, -1, -1; row += 1
        inequality[row, u], inequality[row, v], inequality[row, x] = -1, 1, -1; row += 1
        inequality[row, u], inequality[row, v], inequality[row, x] = -1, -1, 1; row += 1
        inequality[row, u], inequality[row, v], inequality[row, x] = 1, 1, 1; rhs[row] = 2; row += 1
    for i, j, k, kind in active:
        ij, ik, jk = pair_index[(i, j)], pair_index[(i, k)], pair_index[(j, k)]
        if kind == 0:
            inequality[row, ij], inequality[row, ik], inequality[row, jk] = 1, -1, -1
        elif kind == 1:
            inequality[row, ik], inequality[row, ij], inequality[row, jk] = 1, -1, -1
        elif kind == 2:
            inequality[row, jk], inequality[row, ij], inequality[row, ik] = 1, -1, -1
        else:
            inequality[row, ij], inequality[row, ik], inequality[row, jk] = 1, 1, 1; rhs[row] = 2
        row += 1
    equality = lil_matrix((1, variable_count), dtype=float)
    for pair in pairs:
        equality[0, pair_index[pair]] = 1
    bounds = [(0.0, 1.0)] * variable_count
    for qubit, fragment in fixed.items():
        bounds[qubit] = (float(fragment), float(fragment))
    build_time = perf_counter() - built_at
    solved_at = perf_counter()
    raw = linprog(costs, A_ub=inequality.tocsr(), b_ub=rhs, A_eq=equality.tocsr(), b_eq=[(n // 2) * ((n + 1) // 2)], bounds=bounds, method="highs")
    solve_time = perf_counter() - solved_at
    if raw.status == 2:
        return LPRelaxationResult("infeasible", None, None, variable_count, row + 1), build_time, solve_time
    if raw.status != 0 or raw.x is None:
        raise RuntimeError(f"HiGHS LP failed: status={raw.status}, message={raw.message}")
    assignments = tuple((1.0 - float(raw.x[q]), float(raw.x[q])) for q in range(n))
    cuts = {pair: float(raw.x[pair_index[pair]]) for pair in pairs}
    result = _with_fractionality(LPRelaxationResult("optimal", float(raw.fun), assignments, variable_count, row + 1, cuts))
    return result, build_time, solve_time


def _triangle_violations(
    cuts: Mapping[tuple[int, int], float], n: int, tolerance: float
) -> list[tuple[float, tuple[int, int, int, int]]]:
    violations = []
    for i, j, k in combinations(range(n), 3):
        ij, ik, jk = cuts[(i, j)], cuts[(i, k)], cuts[(j, k)]
        for kind, value in enumerate((ij - ik - jk, ik - ij - jk, jk - ij - ik, ij + ik + jk - 2)):
            if value > tolerance:
                violations.append((value, (i, j, k, kind)))
    return sorted(violations, reverse=True)


def _with_fractionality(result: LPRelaxationResult) -> LPRelaxationResult:
    if result.assignments is None:
        return result
    values = [second for _, second in result.assignments]
    fractionalities = [min(value, 1.0 - value) for value in values]
    return LPRelaxationResult(
        result.status, result.lower_bound_log, result.assignments, result.variable_count,
        result.constraint_count, result.cut_values,
        sum(value > 1e-9 for value in fractionalities), max(fractionalities, default=0.0),
    )


def _assignment_index(qubit: int, fragment: int) -> int:
    return 2 * qubit + fragment
