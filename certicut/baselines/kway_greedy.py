"""Deterministic capacity-exact weighted K-way graph-partitioning heuristic."""

from __future__ import annotations

from time import perf_counter
from typing import Sequence

from certicut.graph.interaction import InteractionGraph, graph_partition_objective
from certicut.evaluation.canonical import evaluate_independent_qpd


def solve_weighted_kway_greedy(
    graph: InteractionGraph,
    *,
    capacities: Sequence[int],
    seed: int = 0,
    restarts: int = 4,
    time_limit_s: float | None = None,
) -> tuple[tuple[int, ...], float, float]:
    """Return capacity-exact multistart greedy partition plus swap refinement.

    This is a standalone weighted K-way heuristic baseline. It always meets the
    supplied exact capacity vector and supplies no optimality claim or bound.
    """
    targets = tuple(capacities)
    if not targets or sum(targets) != graph.num_qubits or any(target < 0 for target in targets):
        raise ValueError("capacities must be nonnegative and sum to graph width")
    if restarts < 1:
        raise ValueError("restarts must be positive")
    if time_limit_s is not None and time_limit_s <= 0:
        raise ValueError("time_limit_s must be positive")
    started = perf_counter()
    deadline = None if time_limit_s is None else started + time_limit_s
    weighted_degree = {node.qubit: node.weighted_degree for node in graph.nodes}
    adjacency = [[] for _ in range(graph.num_qubits)]
    for edge in graph.edges:
        adjacency[edge.u].append((edge.v, edge.qpd_log_cost))
        adjacency[edge.v].append((edge.u, edge.qpd_log_cost))
    candidates = []
    restart = 0
    while restart < restarts and (deadline is None or restart == 0 or perf_counter() < deadline):
        order = sorted(range(graph.num_qubits), key=lambda qubit: _order_key(qubit, weighted_degree[qubit], seed, restart))
        labels = [-1] * graph.num_qubits
        loads = [0] * len(targets)
        for qubit in order:
            choices = []
            for fragment, target in enumerate(targets):
                if loads[fragment] == target:
                    continue
                incremental = sum(weight for neighbor, weight in adjacency[qubit] if labels[neighbor] >= 0 and labels[neighbor] != fragment)
                choices.append((incremental, loads[fragment] / max(target, 1), fragment))
            if not choices:
                raise RuntimeError("capacity assignment became infeasible")
            fragment = min(choices)[2]
            labels[qubit] = fragment
            loads[fragment] += 1
        refined = _swap_refine(graph, tuple(labels), targets, deadline)
        candidates.append((graph_partition_objective(graph, refined), refined))
        restart += 1
    objective, partition = min(candidates, key=lambda item: (item[0], item[1]))
    # The public legacy tuple API remains; baseline suites use canonical evaluation.
    evaluate_independent_qpd(graph, partition, targets)
    return partition, objective, perf_counter() - started


def _order_key(qubit: int, degree: float, seed: int, restart: int) -> tuple[float, int]:
    # Deterministic integer mix supplies diversified but reproducible orderings.
    mixed = ((qubit + 1) * 1_103_515_245 + (seed + restart * 17) * 12_345) & 0x7FFFFFFF
    return (-degree if restart % 2 == 0 else degree, mixed)


def _swap_refine(
    graph: InteractionGraph,
    partition: tuple[int, ...],
    capacities: tuple[int, ...],
    deadline: float | None = None,
) -> tuple[int, ...]:
    labels = list(partition)
    while True:
        current = graph_partition_objective(graph, labels)
        best = (0.0, None, None)
        for first in range(graph.num_qubits):
            for second in range(first + 1, graph.num_qubits):
                if deadline is not None and perf_counter() >= deadline:
                    return tuple(labels)
                if labels[first] == labels[second]:
                    continue
                candidate = labels.copy()
                candidate[first], candidate[second] = candidate[second], candidate[first]
                gain = current - graph_partition_objective(graph, candidate)
                if gain > best[0] + 1e-12:
                    best = gain, first, second
        if best[1] is None:
            return tuple(labels)
        labels[best[1]], labels[best[2]] = labels[best[2]], labels[best[1]]
