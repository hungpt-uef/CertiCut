"""HiGHS MILP formulation for capacity-constrained weighted graph partitioning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, log
import sys
from typing import Any, Iterator

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from certicut.graph.interaction import InteractionGraph, graph_partition_objective


@dataclass(frozen=True)
class ExactSolution:
    """An exact MILP result; Phase 2 exposes no CertiCut bound certificate."""

    status: str
    num_fragments: int
    qmax: int
    exact_num_fragments: bool
    partition: tuple[int, ...] | None
    fragments: tuple[tuple[int, ...], ...]
    cut_edges: tuple[tuple[int, int], ...]
    cut_instruction_indices: tuple[int, ...]
    objective_log_cost: float | None
    gamma: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def solve_exact_partition(
    graph: InteractionGraph,
    *,
    num_fragments: int,
    qmax: int,
    exact_num_fragments: bool = False,
) -> ExactSolution:
    """Minimize crossed QPD log cost with SciPy/HiGHS MILP."""
    _validate_parameters(graph, num_fragments, qmax)
    if graph.num_qubits > num_fragments * qmax or (
        exact_num_fragments and num_fragments > graph.num_qubits
    ):
        return _infeasible_solution(num_fragments, qmax, exact_num_fragments)

    n = graph.num_qubits
    edge_count = len(graph.edges)
    variable_count = n * num_fragments + edge_count
    costs = np.zeros(variable_count)
    costs[n * num_fragments :] = [edge.qpd_log_cost for edge in graph.edges]
    integrality = np.ones(variable_count)
    lower_bounds = np.zeros(variable_count)
    upper_bounds = np.ones(variable_count)
    lower_bounds[_assignment_index(0, 0, num_fragments)] = 1
    upper_bounds[_assignment_index(0, 0, num_fragments)] = 1

    constraint_count = n + num_fragments + 2 * edge_count * num_fragments
    matrix = lil_matrix((constraint_count, variable_count), dtype=float)
    lower = np.full(constraint_count, -np.inf)
    upper = np.full(constraint_count, np.inf)
    row = 0

    for qubit in range(n):
        for fragment in range(num_fragments):
            matrix[row, _assignment_index(qubit, fragment, num_fragments)] = 1
        lower[row] = upper[row] = 1
        row += 1

    for fragment in range(num_fragments):
        for qubit in range(n):
            matrix[row, _assignment_index(qubit, fragment, num_fragments)] = 1
        lower[row] = 1 if exact_num_fragments else 0
        upper[row] = qmax
        row += 1

    for edge_index, edge in enumerate(graph.edges):
        x_index = n * num_fragments + edge_index
        for fragment in range(num_fragments):
            u_index = _assignment_index(edge.u, fragment, num_fragments)
            v_index = _assignment_index(edge.v, fragment, num_fragments)
            matrix[row, x_index] = 1
            matrix[row, u_index] = -1
            matrix[row, v_index] = 1
            lower[row] = 0
            row += 1
            matrix[row, x_index] = 1
            matrix[row, u_index] = 1
            matrix[row, v_index] = -1
            lower[row] = 0
            row += 1

    result = milp(
        c=costs,
        integrality=integrality,
        bounds=Bounds(lower_bounds, upper_bounds),
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"disp": False},
    )
    if result.status == 2:
        return _infeasible_solution(num_fragments, qmax, exact_num_fragments)
    if result.status != 0 or result.x is None:
        raise RuntimeError(f"HiGHS failed: status={result.status}, message={result.message}")

    partition = tuple(
        next(
            fragment
            for fragment in range(num_fragments)
            if result.x[_assignment_index(qubit, fragment, num_fragments)] > 0.5
        )
        for qubit in range(n)
    )
    cut_edges = tuple(
        (edge.u, edge.v)
        for edge in graph.edges
        if partition[edge.u] != partition[edge.v]
    )
    cut_instruction_indices = tuple(
        instruction_index
        for edge in graph.edges
        if partition[edge.u] != partition[edge.v]
        for instruction_index in edge.instruction_indices
    )
    objective = graph_partition_objective(graph, partition)
    return ExactSolution(
        status="optimal",
        num_fragments=num_fragments,
        qmax=qmax,
        exact_num_fragments=exact_num_fragments,
        partition=partition,
        fragments=tuple(
            tuple(qubit for qubit, label in enumerate(partition) if label == fragment)
            for fragment in range(num_fragments)
        ),
        cut_edges=cut_edges,
        cut_instruction_indices=cut_instruction_indices,
        objective_log_cost=objective,
        gamma=_safe_gamma(objective),
    )


def brute_force_exact_partition(
    graph: InteractionGraph,
    *,
    num_fragments: int,
    qmax: int,
    exact_num_fragments: bool = False,
) -> ExactSolution:
    """Exhaustive reference solver for Phase 2 validation only."""
    _validate_parameters(graph, num_fragments, qmax)
    best_partition: tuple[int, ...] | None = None
    best_objective = float("inf")
    for partition in _valid_partitions(
        graph.num_qubits, num_fragments, qmax, exact_num_fragments
    ):
        objective = graph_partition_objective(graph, partition)
        if objective < best_objective - 1e-12:
            best_partition = partition
            best_objective = objective
    if best_partition is None:
        return _infeasible_solution(num_fragments, qmax, exact_num_fragments)
    return _solution_from_partition(
        graph, best_partition, num_fragments, qmax, exact_num_fragments
    )


def _assignment_index(qubit: int, fragment: int, num_fragments: int) -> int:
    return qubit * num_fragments + fragment


def _validate_parameters(graph: InteractionGraph, num_fragments: int, qmax: int) -> None:
    if graph.num_qubits == 0:
        raise ValueError("graph must contain at least one qubit")
    if num_fragments < 1:
        raise ValueError("num_fragments must be positive")
    if qmax < 1:
        raise ValueError("qmax must be positive")


def _valid_partitions(
    num_qubits: int,
    num_fragments: int,
    qmax: int,
    exact_num_fragments: bool,
) -> Iterator[tuple[int, ...]]:
    """Enumerate canonical labels; fragment zero always contains q0."""
    labels = [0]
    loads = [1] + [0] * (num_fragments - 1)

    def visit(qubit: int, largest_label: int) -> Iterator[tuple[int, ...]]:
        if qubit == num_qubits:
            if not exact_num_fragments or all(load > 0 for load in loads):
                yield tuple(labels)
            return
        for fragment in range(min(largest_label + 2, num_fragments)):
            if loads[fragment] >= qmax:
                continue
            labels.append(fragment)
            loads[fragment] += 1
            yield from visit(qubit + 1, max(largest_label, fragment))
            loads[fragment] -= 1
            labels.pop()

    yield from visit(1, 0)


def _solution_from_partition(
    graph: InteractionGraph,
    partition: tuple[int, ...],
    num_fragments: int,
    qmax: int,
    exact_num_fragments: bool,
) -> ExactSolution:
    cut_edges = tuple(
        (edge.u, edge.v) for edge in graph.edges if partition[edge.u] != partition[edge.v]
    )
    cut_instruction_indices = tuple(
        instruction_index
        for edge in graph.edges
        if partition[edge.u] != partition[edge.v]
        for instruction_index in edge.instruction_indices
    )
    objective = graph_partition_objective(graph, partition)
    return ExactSolution(
        status="optimal",
        num_fragments=num_fragments,
        qmax=qmax,
        exact_num_fragments=exact_num_fragments,
        partition=partition,
        fragments=tuple(
            tuple(qubit for qubit, label in enumerate(partition) if label == fragment)
            for fragment in range(num_fragments)
        ),
        cut_edges=cut_edges,
        cut_instruction_indices=cut_instruction_indices,
        objective_log_cost=objective,
        gamma=_safe_gamma(objective),
    )


def _infeasible_solution(
    num_fragments: int, qmax: int, exact_num_fragments: bool
) -> ExactSolution:
    return ExactSolution(
        status="infeasible",
        num_fragments=num_fragments,
        qmax=qmax,
        exact_num_fragments=exact_num_fragments,
        partition=None,
        fragments=(),
        cut_edges=(),
        cut_instruction_indices=(),
        objective_log_cost=None,
        gamma=None,
    )


def _safe_gamma(objective_log_cost: float) -> float | None:
    if not isfinite(objective_log_cost) or objective_log_cost > log(sys.float_info.max):
        return None
    return exp(objective_log_cost)
