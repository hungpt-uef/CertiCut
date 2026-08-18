"""Independent KaHIP baselines; K-way results receive exact-capacity repair."""

from __future__ import annotations

from time import perf_counter
from typing import Sequence

import kahip

from certicut.baselines.common import BaselineResult, safe_overhead
from certicut.baselines.kway_greedy import _swap_refine
from certicut.evaluation.canonical import evaluate_independent_qpd
from certicut.graph.interaction import InteractionGraph, graph_partition_objective


_MODES = {"fast": kahip.FAST, "eco": kahip.ECO, "strong": kahip.STRONG}


def solve_kahip(graph: InteractionGraph, *, seed: int = 0, mode: str = "strong") -> BaselineResult:
    """Partition CNOT multiplicities with strict two-way unit-weight balance."""
    if mode not in _MODES:
        raise ValueError(f"unsupported KaHIP mode '{mode}'")
    started = perf_counter()
    vwgt, xadj, adjcwgt, adjncy = _to_csr(graph)
    edgecut, blocks = kahip.kaffpa(
        vwgt, xadj, adjcwgt, adjncy, 2, 0.0, True, seed, _MODES[mode]
    )
    runtime = perf_counter() - started
    partition = tuple(int(block) for block in blocks)
    fragment_sizes = tuple(partition.count(label) for label in (0, 1))
    expected = tuple(sorted((graph.num_qubits // 2, (graph.num_qubits + 1) // 2)))
    if tuple(sorted(fragment_sizes)) != expected:
        return BaselineResult(
            f"kahip_{mode}", "A_exact_balanced", "incompatible_balance", runtime, None, None, (),
            fragment_sizes, None, f"KaHIP edgecut={edgecut}; returned balance violates exact Track A semantics."
        )
    objective = graph_partition_objective(graph, partition)
    cuts = tuple(
        index for edge in graph.edges if partition[edge.u] != partition[edge.v] for index in edge.instruction_indices
    )
    return BaselineResult(
        f"kahip_{mode}", "A_exact_balanced", "feasible", runtime, objective, safe_overhead(objective),
        cuts, fragment_sizes, None,
        f"KaHIP edgecut={edgecut} is diagnostic only; objective is recomputed from CertiCut graph log weights."
    )


def solve_kahip_k(
    graph: InteractionGraph,
    *,
    num_fragments: int,
    capacities: tuple[int, ...],
    seed: int = 0,
    mode: str = "strong",
    weight_scale: int = 1_000_000,
    refinement_time_limit_s: float | None = None,
) -> BaselineResult:
    """Run KaHIP, repair to declared capacities, then QPD swap-refine."""
    if mode not in _MODES:
        raise ValueError(f"unsupported KaHIP mode '{mode}'")
    if num_fragments < 2 or len(capacities) != num_fragments or sum(capacities) != graph.num_qubits:
        raise ValueError("capacities must exactly cover graph qubits")
    if weight_scale < 1:
        raise ValueError("weight_scale must be positive")
    if refinement_time_limit_s is not None and refinement_time_limit_s <= 0:
        raise ValueError("refinement_time_limit_s must be positive")
    started = perf_counter()
    vwgt, xadj, adjcwgt, adjncy = _to_csr(graph, qpd_weights=True, weight_scale=weight_scale)
    edgecut, blocks = kahip.kaffpa(vwgt, xadj, adjcwgt, adjncy, num_fragments, 0.0, True, seed, _MODES[mode])
    partition = tuple(int(block) for block in blocks)
    before_sizes = tuple(partition.count(label) for label in range(num_fragments))
    repaired, moves = _repair_exact_capacities(graph, partition, capacities)
    deadline = None if refinement_time_limit_s is None else perf_counter() + refinement_time_limit_s
    refined = _swap_refine(graph, repaired, tuple(capacities), deadline)
    evaluation = evaluate_independent_qpd(graph, refined, capacities)
    runtime = perf_counter() - started
    return BaselineResult(
        "KaHIP-QPD+repair", "K_exact_capacitated", "feasible", runtime,
        evaluation.objective_log_cost, safe_overhead(evaluation.objective_log_cost),
        evaluation.cut_instruction_indices, evaluation.fragment_sizes, None,
        (
            f"KaHIP edgecut={edgecut}; scaled log-QPD weights S={weight_scale}; "
            f"pre-repair sizes={before_sizes}; repair moves={moves}; QPD swap refinement; "
            "reported objective recomputed by canonical evaluator."
        ),
        evaluation.partition,
    )


def _to_csr(
    graph: InteractionGraph,
    *,
    qpd_weights: bool = False,
    weight_scale: int = 1_000_000,
) -> tuple[list[int], list[int], list[int], list[int]]:
    """Map each undirected CNOT-multiplicity edge to two integer-weight CSR arcs."""
    adjacency = [[] for _ in range(graph.num_qubits)]
    for edge in graph.edges:
        multiplicity = max(1, round(weight_scale * edge.qpd_log_cost)) if qpd_weights else edge.gate_count
        adjacency[edge.u].append((edge.v, multiplicity))
        adjacency[edge.v].append((edge.u, multiplicity))
    xadj = [0]
    adjncy, adjcwgt = [], []
    for neighbours in adjacency:
        for target, weight in sorted(neighbours):
            adjncy.append(target)
            adjcwgt.append(weight)
        xadj.append(len(adjncy))
    return [1] * graph.num_qubits, xadj, adjcwgt, adjncy


def _repair_exact_capacities(
    graph: InteractionGraph,
    partition: Sequence[int],
    capacities: Sequence[int],
) -> tuple[tuple[int, ...], int]:
    """Move least-damaging vertices from overfull to underfull fragments."""
    labels = list(partition)
    targets = tuple(capacities)
    if any(label < 0 or label >= len(targets) for label in labels):
        raise ValueError("KaHIP returned an invalid block label")
    loads = [labels.count(fragment) for fragment in range(len(targets))]
    moves = 0
    while loads != list(targets):
        overfull = [fragment for fragment, load in enumerate(loads) if load > targets[fragment]]
        underfull = [fragment for fragment, load in enumerate(loads) if load < targets[fragment]]
        if not overfull or not underfull:
            raise RuntimeError("capacity repair reached inconsistent loads")
        best: tuple[float, int, int, int] | None = None
        for source in overfull:
            for qubit, label in enumerate(labels):
                if label != source:
                    continue
                for target in underfull:
                    delta = _move_delta(graph, labels, qubit, source, target)
                    candidate = (delta, qubit, source, target)
                    if best is None or candidate < best:
                        best = candidate
        assert best is not None
        _, qubit, source, target = best
        labels[qubit] = target
        loads[source] -= 1
        loads[target] += 1
        moves += 1
    return tuple(labels), moves


def _move_delta(
    graph: InteractionGraph,
    partition: Sequence[int],
    qubit: int,
    source: int,
    target: int,
) -> float:
    """Return J change for moving one qubit; positive values worsen J."""
    delta = 0.0
    for edge in graph.edges:
        if edge.u == qubit:
            other = edge.v
        elif edge.v == qubit:
            other = edge.u
        else:
            continue
        old_cut = partition[other] != source
        new_cut = partition[other] != target
        delta += edge.qpd_log_cost * (new_cut - old_cut)
    return delta
