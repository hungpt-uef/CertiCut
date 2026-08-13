"""Safe deterministic primal heuristics; they provide upper bounds only."""

from __future__ import annotations

import numpy as np

from certicut.graph.interaction import InteractionGraph, graph_partition_objective


def greedy_partition(
    graph: InteractionGraph, *, qmax: int, exact_num_fragments: bool
) -> tuple[tuple[int, ...], float] | None:
    """Assign qubits greedily by incremental crossed-edge cost, with q0 fixed to F0."""
    if graph.num_qubits > 2 * qmax:
        return None
    partition = [0]
    loads = [1, 0]
    for qubit in range(1, graph.num_qubits):
        candidates = []
        remaining_after = graph.num_qubits - qubit - 1
        for fragment in (0, 1):
            if loads[fragment] >= qmax:
                continue
            trial_loads = loads.copy()
            trial_loads[fragment] += 1
            if exact_num_fragments and trial_loads[1] == 0 and remaining_after == 0:
                continue
            trial = tuple((*partition, fragment))
            incremental_cost = sum(
                edge.qpd_log_cost
                for edge in graph.edges
                if edge.v == qubit and edge.u < qubit and trial[edge.u] != fragment
            )
            candidates.append((incremental_cost, fragment))
        if not candidates:
            return None
        _, fragment = min(candidates)
        partition.append(fragment)
        loads[fragment] += 1
    if exact_num_fragments and 0 in loads:
        return None
    solution = tuple(partition)
    return solution, graph_partition_objective(graph, solution)


def warm_start_partition(
    graph: InteractionGraph, *, qmax: int, exact_num_fragments: bool, variant: str = "h0"
) -> tuple[tuple[int, ...], float] | None:
    """Return deterministic H0/H1/H2/H3 primal candidate; objective is graph source of truth."""
    if not exact_num_fragments:
        return greedy_partition(graph, qmax=qmax, exact_num_fragments=False)
    targets = tuple(sorted({graph.num_qubits // 2, (graph.num_qubits + 1) // 2}))
    candidates = []
    h0 = greedy_partition(graph, qmax=qmax, exact_num_fragments=True)
    if h0:
        candidates.append(h0)
    if variant in {"h1", "h2", "h3"}:
        orders = _multistart_orders(graph)
        for target in targets:
            for order in orders:
                partition = _construct_balanced(graph, target, order)
                candidates.append((partition, graph_partition_objective(graph, partition)))
    if variant in {"h2", "h3"}:
        candidates = [(_pair_swap_refine(graph, partition), 0.0) for partition, _ in candidates]
        candidates = [(partition, graph_partition_objective(graph, partition)) for partition, _ in candidates]
    if variant == "h3":
        for target in targets:
            partition = _spectral_partition(graph, target)
            partition = _pair_swap_refine(graph, partition)
            candidates.append((partition, graph_partition_objective(graph, partition)))
    if variant not in {"h0", "h1", "h2", "h3"}:
        raise ValueError(f"unknown warm-start variant '{variant}'")
    return min(candidates, key=lambda item: (item[1], item[0])) if candidates else None


def _multistart_orders(graph: InteractionGraph) -> tuple[tuple[int, ...], ...]:
    weighted_degree = {node.qubit: node.weighted_degree for node in graph.nodes}
    degree = {node.qubit: node.degree for node in graph.nodes}
    qubits = tuple(range(1, graph.num_qubits))
    return (
        qubits,
        tuple(sorted(qubits, key=lambda q: (-weighted_degree[q], q))),
        tuple(sorted(qubits, key=lambda q: (-degree[q], q))),
        tuple(sorted(qubits, key=lambda q: (weighted_degree[q], q))),
    )


def _construct_balanced(graph: InteractionGraph, target_f0: int, order: tuple[int, ...]) -> tuple[int, ...]:
    labels: list[int | None] = [None] * graph.num_qubits
    labels[0] = 0
    assigned = {0}
    for qubit in order:
        f0_remaining = target_f0 - sum(label == 0 for label in labels)
        unassigned_after = graph.num_qubits - len(assigned) - 1
        if f0_remaining == 0:
            label = 1
        elif f0_remaining == unassigned_after + 1:
            label = 0
        else:
            costs = []
            for label_candidate in (0, 1):
                incremental = sum(
                    edge.qpd_log_cost
                    for edge in graph.edges
                    if (edge.u == qubit and edge.v in assigned and labels[edge.v] != label_candidate)
                    or (edge.v == qubit and edge.u in assigned and labels[edge.u] != label_candidate)
                )
                costs.append((incremental, label_candidate))
            label = min(costs)[1]
        labels[qubit] = label
        assigned.add(qubit)
    return tuple(label for label in labels if label is not None)


def _pair_swap_refine(graph: InteractionGraph, partition: tuple[int, ...]) -> tuple[int, ...]:
    """Balanced deterministic Kernighan-Lin style best-improving pair swaps."""
    labels = list(partition)
    while True:
        current = graph_partition_objective(graph, labels)
        best = (0.0, None, None)
        f0 = [q for q, label in enumerate(labels) if label == 0 and q != 0]
        f1 = [q for q, label in enumerate(labels) if label == 1]
        for first in f0:
            for second in f1:
                candidate = labels.copy()
                candidate[first], candidate[second] = 1, 0
                gain = current - graph_partition_objective(graph, candidate)
                if gain > best[0] + 1e-12:
                    best = (gain, first, second)
        if best[1] is None:
            return tuple(labels)
        labels[best[1]], labels[best[2]] = 1, 0


def _spectral_partition(graph: InteractionGraph, target_f0: int) -> tuple[int, ...]:
    n = graph.num_qubits
    weights = np.zeros((n, n))
    for edge in graph.edges:
        weights[edge.u, edge.v] = weights[edge.v, edge.u] = edge.qpd_log_cost
    laplacian = np.diag(weights.sum(axis=1)) - weights
    _, vectors = np.linalg.eigh(laplacian)
    fiedler = vectors[:, 1] if n > 1 else np.zeros(1)
    f0 = {0}
    remaining = [q for q in range(1, n)]
    # Keep q0 in F0; choose the remaining target slots closest to q0's Fiedler coordinate.
    remaining.sort(key=lambda q: (abs(fiedler[q] - fiedler[0]), q))
    f0.update(remaining[: target_f0 - 1])
    return tuple(0 if q in f0 else 1 for q in range(n))
