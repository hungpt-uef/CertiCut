"""Small direct gate-occurrence oracle for the restricted gate-only model."""

from __future__ import annotations

from dataclasses import dataclass
from math import inf
from typing import Iterator, Sequence

from certicut.graph.interaction import InteractionGraph


@dataclass(frozen=True)
class RestrictedExactResult:
    partition: tuple[int, ...]
    direct_gate_log_cost: float
    graph_log_cost: float


def solve_restricted_gate_only_exact(
    graph: InteractionGraph,
    *,
    capacities: Sequence[int],
    max_qubits: int = 10,
) -> RestrictedExactResult:
    """Enumerate exact-capacity placements, summing individual gate occurrences.

    This is a restricted gate-only independent formulation check, not a
    reproduction of Brandhofer et al.'s broader gate/wire/ancilla model.
    """
    targets = tuple(capacities)
    if not targets or sum(targets) != graph.num_qubits or any(target < 0 for target in targets):
        raise ValueError("capacities must be nonnegative and sum to graph width")
    if graph.num_qubits > max_qubits:
        raise ValueError(f"direct exact oracle is limited to n <= {max_qubits}")
    best_partition: tuple[int, ...] | None = None
    best_cost = inf
    for partition in _exact_capacity_partitions(graph.num_qubits, targets):
        cost = sum(
            gate.qpd_log_cost
            for edge in graph.edges
            if partition[edge.u] != partition[edge.v]
            for gate in edge.gates
        )
        if cost < best_cost - 1e-12:
            best_cost, best_partition = cost, partition
    if best_partition is None:
        raise RuntimeError("exact-capacity enumeration found no partition")
    graph_cost = sum(
        edge.qpd_log_cost for edge in graph.edges if best_partition[edge.u] != best_partition[edge.v]
    )
    return RestrictedExactResult(best_partition, best_cost, graph_cost)


def _exact_capacity_partitions(num_qubits: int, capacities: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    labels = [-1] * num_qubits
    loads = [0] * len(capacities)

    def visit(qubit: int) -> Iterator[tuple[int, ...]]:
        if qubit == num_qubits:
            yield tuple(labels)
            return
        for fragment, capacity in enumerate(capacities):
            if loads[fragment] == capacity:
                continue
            labels[qubit] = fragment
            loads[fragment] += 1
            yield from visit(qubit + 1)
            loads[fragment] -= 1
            labels[qubit] = -1

    yield from visit(0)
