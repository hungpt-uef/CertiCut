"""One evaluator for matched capacitated independent-QPD baselines."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log
from typing import Sequence

from certicut.graph.interaction import InteractionGraph, graph_partition_objective


@dataclass(frozen=True)
class CanonicalEvaluation:
    partition: tuple[int, ...]
    fragment_sizes: tuple[int, ...]
    objective_log_cost: float
    cut_instruction_indices: tuple[int, ...]


def evaluate_independent_qpd(
    graph: InteractionGraph,
    partition: Sequence[int],
    capacities: Sequence[int],
) -> CanonicalEvaluation:
    """Validate exact capacities then recompute the graph-independent-QPD objective."""
    labels = tuple(partition)
    targets = tuple(capacities)
    if len(labels) != graph.num_qubits:
        raise ValueError("partition length must equal graph width")
    if not targets or sum(targets) != graph.num_qubits:
        raise ValueError("capacities must exactly cover graph width")
    if any(label < 0 or label >= len(targets) for label in labels):
        raise ValueError("partition contains an invalid fragment label")
    sizes = tuple(labels.count(fragment) for fragment in range(len(targets)))
    if sizes != targets:
        raise ValueError(f"partition capacities {sizes} do not match declared {targets}")
    return CanonicalEvaluation(
        partition=labels,
        fragment_sizes=sizes,
        objective_log_cost=graph_partition_objective(graph, labels),
        cut_instruction_indices=tuple(
            instruction_index
            for edge in graph.edges
            if labels[edge.u] != labels[edge.v]
            for instruction_index in edge.instruction_indices
        ),
    )


def log10_regret_upper_bound(objective: float, lower_bound: float | None) -> float | None:
    """Return a certified log10 factor when a finite lower bound is available."""
    if lower_bound is None or not isfinite(lower_bound):
        return None
    return (objective - lower_bound) / log(10.0)


def sampling_overhead(log_cost: float) -> float | None:
    """Exponentiate only when the IEEE double result remains finite."""
    return exp(log_cost) if log_cost <= log(float.fromhex("0x1.fffffffffffffp+1023")) else None
