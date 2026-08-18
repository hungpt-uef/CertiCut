"""Capacity-exact K-way pairwise Kernighan--Lin baselines."""

from __future__ import annotations

from random import Random
from time import perf_counter
from typing import Literal, Sequence

from certicut.baselines.common import BaselineResult, safe_overhead
from certicut.evaluation.canonical import evaluate_independent_qpd
from certicut.graph.interaction import InteractionGraph


WeightMode = Literal["count", "qpd"]
_EPSILON = 1e-12


def solve_kway_kl(
    graph: InteractionGraph,
    *,
    capacities: Sequence[int],
    weight_mode: WeightMode,
    seed: int = 0,
    restarts: int = 4,
    time_limit_s: float | None = None,
) -> BaselineResult:
    """Run multistart pairwise-block KL; report only canonical QPD metrics.

    Each pass locks swap endpoints, retains the best cumulative prefix, and may
    cross a temporary uphill move. This is intentionally distinct from greedy
    best-improving swap refinement.
    """
    targets = tuple(capacities)
    if not targets or sum(targets) != graph.num_qubits or any(target < 0 for target in targets):
        raise ValueError("capacities must be nonnegative and sum to graph width")
    if weight_mode not in {"count", "qpd"}:
        raise ValueError("weight_mode must be 'count' or 'qpd'")
    if restarts < 1:
        raise ValueError("restarts must be positive")
    if time_limit_s is not None and time_limit_s <= 0:
        raise ValueError("time_limit_s must be positive")

    started = perf_counter()
    deadline = None if time_limit_s is None else started + time_limit_s
    best: tuple[float, tuple[int, ...]] | None = None
    restart = 0
    while restart < restarts and (deadline is None or restart == 0 or perf_counter() < deadline):
        labels = _random_exact_capacity_partition(graph.num_qubits, targets, seed + restart)
        labels = _sweep_pairwise_kl(graph, labels, weight_mode, deadline)
        score = _objective(graph, labels, weight_mode)
        candidate = (score, labels)
        if best is None or candidate < best:
            best = candidate
        restart += 1
        if deadline is None and restart >= restarts:
            break
    if best is None:
        raise RuntimeError("KL did not complete an initial partition")
    evaluation = evaluate_independent_qpd(graph, best[1], targets)
    return BaselineResult(
        method="Froehler-KL-count" if weight_mode == "count" else "KL-QPD",
        track="K_exact_capacitated",
        status="feasible",
        runtime_s=perf_counter() - started,
        objective_log_cost=evaluation.objective_log_cost,
        sampling_overhead=safe_overhead(evaluation.objective_log_cost),
        cut_instruction_indices=evaluation.cut_instruction_indices,
        fragment_sizes=evaluation.fragment_sizes,
        minimum_reached=None,
        notes=(
            f"K-way pairwise KL adaptation; internal objective={weight_mode}; "
            f"restarts={restart}; temporary uphill swaps permitted."
        ),
        partition=evaluation.partition,
    )


def _random_exact_capacity_partition(num_qubits: int, capacities: tuple[int, ...], seed: int) -> tuple[int, ...]:
    qubits = list(range(num_qubits))
    Random(seed).shuffle(qubits)
    labels = [-1] * num_qubits
    offset = 0
    for fragment, capacity in enumerate(capacities):
        for qubit in qubits[offset:offset + capacity]:
            labels[qubit] = fragment
        offset += capacity
    return tuple(labels)


def _sweep_pairwise_kl(
    graph: InteractionGraph,
    initial: tuple[int, ...],
    weight_mode: WeightMode,
    deadline: float | None,
) -> tuple[int, ...]:
    labels = initial
    while deadline is None or perf_counter() < deadline:
        improved = False
        for first in range(max(labels) + 1):
            for second in range(first + 1, max(labels) + 1):
                if deadline is not None and perf_counter() >= deadline:
                    return labels
                candidate = _kl_pair_pass(graph, labels, first, second, weight_mode, deadline)
                if _objective(graph, candidate, weight_mode) < _objective(graph, labels, weight_mode) - _EPSILON:
                    labels = candidate
                    improved = True
        if not improved:
            return labels
    return labels


def _kl_pair_pass(
    graph: InteractionGraph,
    initial: tuple[int, ...],
    first: int,
    second: int,
    weight_mode: WeightMode,
    deadline: float | None = None,
) -> tuple[int, ...]:
    labels = list(initial)
    unlocked_first = {qubit for qubit, label in enumerate(labels) if label == first}
    unlocked_second = {qubit for qubit, label in enumerate(labels) if label == second}
    if not unlocked_first or not unlocked_second:
        return initial
    current = _objective(graph, labels, weight_mode)
    cumulative = 0.0
    best_cumulative = 0.0
    best_partition = initial
    while unlocked_first and unlocked_second:
        best_move: tuple[float, int, int, float] | None = None
        for left in sorted(unlocked_first):
            for right in sorted(unlocked_second):
                if deadline is not None and perf_counter() >= deadline:
                    return best_partition
                trial = labels.copy()
                trial[left], trial[right] = trial[right], trial[left]
                next_value = _objective(graph, trial, weight_mode)
                gain = current - next_value
                move = (gain, -left, -right, next_value)
                if best_move is None or move > best_move:
                    best_move = move
        assert best_move is not None
        gain, negative_left, negative_right, next_value = best_move
        left, right = -negative_left, -negative_right
        labels[left], labels[right] = labels[right], labels[left]
        unlocked_first.remove(left)
        unlocked_second.remove(right)
        current = next_value
        cumulative += gain
        if cumulative > best_cumulative + _EPSILON:
            best_cumulative = cumulative
            best_partition = tuple(labels)
    return best_partition


def _objective(graph: InteractionGraph, partition: Sequence[int], weight_mode: WeightMode) -> float:
    if weight_mode == "qpd":
        return sum(edge.qpd_log_cost for edge in graph.edges if partition[edge.u] != partition[edge.v])
    return float(sum(edge.gate_count for edge in graph.edges if partition[edge.u] != partition[edge.v]))
