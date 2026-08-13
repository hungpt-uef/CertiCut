"""Independent KaHIP weighted balanced-bisection baseline for CNOT-only Track A."""

from __future__ import annotations

from time import perf_counter

import kahip

from certicut.baselines.common import BaselineResult, safe_overhead
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
) -> BaselineResult:
    """Run KaHIP K-way heuristic then recompute CertiCut's QPD objective."""
    if mode not in _MODES:
        raise ValueError(f"unsupported KaHIP mode '{mode}'")
    if num_fragments < 2 or len(capacities) != num_fragments or sum(capacities) != graph.num_qubits:
        raise ValueError("capacities must exactly cover graph qubits")
    started = perf_counter()
    vwgt, xadj, adjcwgt, adjncy = _to_csr(graph, qpd_weights=True)
    edgecut, blocks = kahip.kaffpa(vwgt, xadj, adjcwgt, adjncy, num_fragments, 0.0, True, seed, _MODES[mode])
    runtime = perf_counter() - started
    partition = tuple(int(block) for block in blocks)
    fragment_sizes = tuple(partition.count(label) for label in range(num_fragments))
    if tuple(sorted(fragment_sizes)) != tuple(sorted(capacities)):
        return BaselineResult(
            f"kahip_k{num_fragments}_{mode}", "K_exact_capacitated", "incompatible_balance", runtime, None, None, (),
            fragment_sizes, None, f"KaHIP edgecut={edgecut}; returned capacities do not match declared multiset."
        )
    objective = graph_partition_objective(graph, partition)
    cuts = tuple(index for edge in graph.edges if partition[edge.u] != partition[edge.v] for index in edge.instruction_indices)
    return BaselineResult(
        f"kahip_k{num_fragments}_{mode}", "K_exact_capacitated", "feasible", runtime, objective, safe_overhead(objective),
        cuts, fragment_sizes, None,
        "KaHIP uses scaled integer log-QPD weights; CertiCut recomputes the reported objective from graph costs."
    )


def _to_csr(graph: InteractionGraph, *, qpd_weights: bool = False) -> tuple[list[int], list[int], list[int], list[int]]:
    """Map each undirected CNOT-multiplicity edge to two integer-weight CSR arcs."""
    adjacency = [[] for _ in range(graph.num_qubits)]
    for edge in graph.edges:
        multiplicity = max(1, round(1_000_000 * edge.qpd_log_cost)) if qpd_weights else edge.gate_count
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
