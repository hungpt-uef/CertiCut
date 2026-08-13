"""Solver-integrated hardware-aware joint-cutting hypergraph MILP."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from certicut.graph.hypergraph import Hyperedge, Hypergraph


@dataclass(frozen=True)
class QPUSpec:
    """Frozen logical-capacity, physical-topology, and calibration data for one QPU."""

    qpu_id: int
    capacity: int
    coupling_edges: tuple[tuple[int, int], ...] = ()
    gate_error_rates: Mapping[tuple[int, int], float] | None = None
    readout_error_rates: Mapping[int, float] | None = None
    physical_qubits: tuple[int, ...] = ()

    def sites(self) -> tuple[int, ...]:
        """Return deterministic physical sites, including isolated calibrated qubits."""
        if self.physical_qubits:
            return tuple(sorted(set(self.physical_qubits)))
        labels = {site for edge in self.coupling_edges for site in edge}
        labels.update((self.readout_error_rates or {}).keys())
        return tuple(sorted(labels)) if labels else tuple(range(self.capacity))


@dataclass(frozen=True)
class HypergraphMILPSolution:
    """Optimal solution and separated solver-integrated objective components."""

    status: str
    num_qpus: int
    partition: tuple[int, ...] | None
    fragments: tuple[tuple[int, ...], ...]
    physical_placements: tuple[tuple[int, int] | None, ...]
    cut_hyperedge_ids: tuple[int, ...]
    objective_value: float | None
    cut_cost: float | None
    routing_cost: float | None
    readout_error_cost: float | None
    gate_error_cost: float | None
    swap_cost_estimate: float | None
    error_cost: float | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def estimate_swap_count(fragment_qubits: Sequence[int], qpu_spec: QPUSpec | None) -> float:
    """Legacy diagnostic only; Phase 10.2 optimizes routing through placement variables."""
    if len(fragment_qubits) <= 1 or qpu_spec is None:
        return 0.0
    hardware = _hardware_cost(qpu_spec)
    count = min(len(fragment_qubits), len(hardware.sites))
    if count < 2:
        return 0.0
    distances = [hardware.distance[u, v] for u in range(count) for v in range(u + 1, count)]
    return float(sum(max(distance - 1.0, 0.0) for distance in distances))


@dataclass(frozen=True)
class _HardwareCost:
    sites: tuple[int, ...]
    distance: np.ndarray
    direct_error: np.ndarray
    routed_gate_error: np.ndarray


def _hardware_cost(spec: QPUSpec) -> _HardwareCost:
    sites = spec.sites()
    if not sites:
        raise ValueError("QPU must expose at least one physical site")
    index = {site: idx for idx, site in enumerate(sites)}
    size = len(sites)
    distance = np.full((size, size), np.inf)
    np.fill_diagonal(distance, 0.0)
    errors = np.full((size, size), np.nan)
    rates = spec.gate_error_rates or {}
    for first, second in spec.coupling_edges:
        if first not in index or second not in index:
            raise ValueError("coupling edge contains a site omitted from physical_qubits")
        u, v = index[first], index[second]
        distance[u, v] = distance[v, u] = 1.0
        rate = rates.get((first, second), rates.get((second, first), 0.01))
        errors[u, v] = errors[v, u] = float(rate)
    for pivot in range(size):
        distance = np.minimum(distance, distance[:, [pivot]] + distance[[pivot], :])
    finite_errors = errors[np.isfinite(errors)]
    default_error = float(np.min(finite_errors)) if finite_errors.size else 0.01
    direct_error = np.where(np.isfinite(errors), errors, default_error)
    routed_gate_error = np.where(
        distance == 1.0,
        direct_error,
        np.where(
            np.isfinite(distance),
            (3.0 * np.maximum(distance - 1.0, 0.0) + 1.0) * default_error,
            1e6,
        ),
    )
    return _HardwareCost(sites, distance, direct_error, routed_gate_error)


def _joint_assignment_cost(edge: Hyperedge, assignment: tuple[int, ...]) -> float:
    """Symmetric K-way joint-block cost from exact precomputed bipartition ranks."""
    labels = set(assignment)
    if len(labels) == 1:
        return 0.0
    by_qpu = {
        qpu: tuple(qubit for qubit, label in zip(edge.qubits, assignment, strict=True) if label == qpu)
        for qpu in labels
    }
    # Sum one-vs-rest operator costs, divided by two so K=2 is exactly log(rank).
    values: list[float] = []
    anchor = edge.qubits[0]
    for subset in by_qpu.values():
        canonical = subset if anchor in subset else tuple(q for q in edge.qubits if q not in subset)
        values.append(edge.log_rank_for_partition(canonical))
    return 0.5 * sum(values)


def solve_max_k_cut_unbalanced(
    hypergraph: Hypergraph,
    *,
    num_qpus: int = 2,
    qpu_capacities: Sequence[int] | None = None,
    qpu_specs: Sequence[QPUSpec] | None = None,
    alpha: float = 1.0,
    beta: float = 0.5,
    gamma: float = 0.5,
    delta: float = 0.5,
    require_nonempty_qpus: bool = False,
    max_joint_block_qubits: int = 3,
) -> HypergraphMILPSolution:
    """Minimize joint-cut, routing, readout, and gate-error costs in one MILP.

    `z[i,k,u]` places logical qubit `i` at physical site `u` on QPU `k`.
    Pair-placement variables exactly linearize routing and gate-error contributions.
    Joint-pattern variables exactly select a QPU assignment pattern for every hyperedge
    of arity at most `max_joint_block_qubits`.
    """
    n = hypergraph.num_qubits
    if num_qpus < 1:
        raise ValueError("num_qpus must be positive")
    if any(value < 0 for value in (alpha, beta, gamma, delta)):
        raise ValueError("objective weights must be nonnegative")
    if any(len(edge.qubits) > max_joint_block_qubits for edge in hypergraph.hyperedges):
        raise ValueError("hyperedge exceeds max_joint_block_qubits; avoid exponential pattern expansion")

    if qpu_specs is None:
        default_capacity = (n + num_qpus - 1) // num_qpus + 2
        specs = tuple(QPUSpec(k, default_capacity) for k in range(num_qpus))
    else:
        specs = tuple(qpu_specs)
        if len(specs) != num_qpus or tuple(spec.qpu_id for spec in specs) != tuple(range(num_qpus)):
            raise ValueError("qpu_specs must be ordered and identified by 0..num_qpus-1")
    capacities = tuple(qpu_capacities) if qpu_capacities is not None else tuple(spec.capacity for spec in specs)
    if len(capacities) != num_qpus or any(capacity < 0 for capacity in capacities):
        raise ValueError("qpu_capacities must contain one nonnegative value per QPU")
    if sum(capacities) < n:
        return _infeasible(num_qpus)

    hardware = tuple(_hardware_cost(spec) for spec in specs)
    if any(len(cost.sites) < capacity for cost, capacity in zip(hardware, capacities, strict=True)):
        raise ValueError("logical capacity cannot exceed available physical sites")

    # Variable registry.
    names: dict[tuple[Any, ...], int] = {}
    costs: list[float] = []

    def add(name: tuple[Any, ...], coefficient: float = 0.0) -> int:
        names[name] = len(costs)
        costs.append(coefficient)
        return names[name]

    y = {(i, k): add(("y", i, k)) for i in range(n) for k in range(num_qpus)}
    z = {
        (i, k, u): add(("z", i, k, u), gamma * (specs[k].readout_error_rates or {}).get(site, 0.0))
        for i in range(n)
        for k in range(num_qpus)
        for u, site in enumerate(hardware[k].sites)
    }
    x = {edge.edge_id: add(("x", edge.edge_id)) for edge in hypergraph.hyperedges}

    patterns = {
        edge.edge_id: tuple(product(range(num_qpus), repeat=len(edge.qubits)))
        for edge in hypergraph.hyperedges
    }
    h = {
        (edge.edge_id, pattern): add(("h", edge.edge_id, pattern), alpha * _joint_assignment_cost(edge, pattern))
        for edge in hypergraph.hyperedges
        for pattern in patterns[edge.edge_id]
    }

    pair_occurrences = [
        (edge, first, second, count)
        for edge in hypergraph.hyperedges
        for first, second, count in edge.pair_gate_counts
    ]
    p: dict[tuple[int, int, int, int, int], int] = {}
    for occurrence_id, (_, _, _, multiplicity) in enumerate(pair_occurrences):
        for k, costs_k in enumerate(hardware):
            for u in range(len(costs_k.sites)):
                for v in range(len(costs_k.sites)):
                    if u == v:
                        continue
                    reachable = np.isfinite(costs_k.distance[u, v])
                    routing = max(costs_k.distance[u, v] - 1.0, 0.0) if reachable else 0.0
                    routing_term = beta * routing if reachable else (1e6 if beta > 0 else 0.0)
                    gate_term = delta * costs_k.routed_gate_error[u, v] if reachable else (1e6 if delta > 0 else 0.0)
                    coefficient = multiplicity * (routing_term + gate_term)
                    p[(occurrence_id, k, u, v, 0)] = add(("p", occurrence_id, k, u, v), coefficient)

    # Number of linear constraints before allocation.
    constraint_count = n + num_qpus + n * num_qpus + sum(len(cost.sites) for cost in hardware)
    if require_nonempty_qpus:
        constraint_count += num_qpus
    constraint_count += sum(1 + len(edge.qubits) * num_qpus + 1 for edge in hypergraph.hyperedges)
    constraint_count += 3 * len(p)
    matrix = lil_matrix((constraint_count, len(costs)), dtype=float)
    lower = np.full(constraint_count, -np.inf)
    upper = np.full(constraint_count, np.inf)
    row = 0

    # Exactly one QPU per logical qubit.
    for i in range(n):
        for k in range(num_qpus):
            matrix[row, y[i, k]] = 1.0
        lower[row] = upper[row] = 1.0
        row += 1
    # QPU logical capacity and optional nonempty use.
    for k in range(num_qpus):
        for i in range(n):
            matrix[row, y[i, k]] = 1.0
        lower[row], upper[row] = 0.0, capacities[k]
        row += 1
    if require_nonempty_qpus:
        for k in range(num_qpus):
            for i in range(n):
                matrix[row, y[i, k]] = 1.0
            lower[row] = 1.0
            row += 1
    # Link QPU assignment to exactly one physical placement.
    for i in range(n):
        for k, costs_k in enumerate(hardware):
            matrix[row, y[i, k]] = -1.0
            for u in range(len(costs_k.sites)):
                matrix[row, z[i, k, u]] = 1.0
            lower[row] = upper[row] = 0.0
            row += 1
    # No physical site hosts two logical qubits.
    for k, costs_k in enumerate(hardware):
        for u in range(len(costs_k.sites)):
            for i in range(n):
                matrix[row, z[i, k, u]] = 1.0
            lower[row], upper[row] = 0.0, 1.0
            row += 1

    # Exact joint-pattern selection and its x_e cut indicator.
    for edge in hypergraph.hyperedges:
        edge_patterns = patterns[edge.edge_id]
        for pattern in edge_patterns:
            matrix[row, h[edge.edge_id, pattern]] = 1.0
        lower[row] = upper[row] = 1.0
        row += 1
        for local_i, logical_i in enumerate(edge.qubits):
            for k in range(num_qpus):
                matrix[row, y[logical_i, k]] = -1.0
                for pattern in edge_patterns:
                    if pattern[local_i] == k:
                        matrix[row, h[edge.edge_id, pattern]] += 1.0
                lower[row] = upper[row] = 0.0
                row += 1
        matrix[row, x[edge.edge_id]] = -1.0
        for pattern in edge_patterns:
            if len(set(pattern)) > 1:
                matrix[row, h[edge.edge_id, pattern]] += 1.0
        lower[row] = upper[row] = 0.0
        row += 1

    # Exact AND linearization p = z[first,k,u] AND z[second,k,v].
    for occurrence_id, (_, first, second, _) in enumerate(pair_occurrences):
        for k, costs_k in enumerate(hardware):
            for u in range(len(costs_k.sites)):
                for v in range(len(costs_k.sites)):
                    if u == v:
                        continue
                    p_var = p[(occurrence_id, k, u, v, 0)]
                    matrix[row, p_var], matrix[row, z[first, k, u]] = 1.0, -1.0
                    upper[row] = 0.0
                    row += 1
                    matrix[row, p_var], matrix[row, z[second, k, v]] = 1.0, -1.0
                    upper[row] = 0.0
                    row += 1
                    matrix[row, p_var] = 1.0
                    matrix[row, z[first, k, u]] = -1.0
                    matrix[row, z[second, k, v]] = -1.0
                    lower[row] = -1.0
                    row += 1

    assert row == constraint_count
    bounds = Bounds(np.zeros(len(costs)), np.ones(len(costs)))
    # Label symmetry only; it does not constrain physical-site choice.
    bounds.lb[y[0, 0]] = bounds.ub[y[0, 0]] = 1.0
    for k in range(1, num_qpus):
        bounds.lb[y[0, k]] = bounds.ub[y[0, k]] = 0.0
    result = milp(
        c=np.asarray(costs),
        integrality=np.ones(len(costs)),
        bounds=bounds,
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"disp": False},
    )
    if result.status == 2 or result.x is None:
        return _infeasible(num_qpus)
    if result.status != 0:
        raise RuntimeError(f"HiGHS MILP failed: status={result.status}, message={result.message}")

    partition = tuple(next(k for k in range(num_qpus) if result.x[y[i, k]] > 0.5) for i in range(n))
    placements = tuple(
        next(
            (k, costs_k.sites[u])
            for k, costs_k in enumerate(hardware)
            for u in range(len(costs_k.sites))
            if result.x[z[i, k, u]] > 0.5
        )
        for i in range(n)
    )
    fragments = tuple(tuple(i for i, label in enumerate(partition) if label == k) for k in range(num_qpus))
    cut_ids = tuple(edge.edge_id for edge in hypergraph.hyperedges if result.x[x[edge.edge_id]] > 0.5)
    joint_cut_cost = sum(
        _joint_assignment_cost(edge, next(pattern for pattern in patterns[edge.edge_id] if result.x[h[edge.edge_id, pattern]] > 0.5))
        for edge in hypergraph.hyperedges
    )
    routing_cost = sum(
        multiplicity * (max(hardware[k].distance[u, v] - 1.0, 0.0) if np.isfinite(hardware[k].distance[u, v]) else 0.0) * result.x[p[(occurrence_id, k, u, v, 0)]]
        for occurrence_id, (_, _, _, multiplicity) in enumerate(pair_occurrences)
        for k, costs_k in enumerate(hardware)
        for u in range(len(costs_k.sites))
        for v in range(len(costs_k.sites)) if u != v
    )
    readout_cost = sum(
        (specs[k].readout_error_rates or {}).get(hardware[k].sites[u], 0.0) * result.x[z[i, k, u]]
        for i in range(n)
        for k in range(num_qpus)
        for u in range(len(hardware[k].sites))
    )
    gate_cost = sum(
        multiplicity * (hardware[k].routed_gate_error[u, v] if np.isfinite(hardware[k].distance[u, v]) else 0.0) * result.x[p[(occurrence_id, k, u, v, 0)]]
        for occurrence_id, (_, _, _, multiplicity) in enumerate(pair_occurrences)
        for k, costs_k in enumerate(hardware)
        for u in range(len(costs_k.sites))
        for v in range(len(costs_k.sites)) if u != v
    )
    return HypergraphMILPSolution(
        status="optimal",
        num_qpus=num_qpus,
        partition=partition,
        fragments=fragments,
        physical_placements=placements,
        cut_hyperedge_ids=cut_ids,
        objective_value=float(result.fun),
        cut_cost=float(joint_cut_cost),
        routing_cost=float(routing_cost),
        readout_error_cost=float(readout_cost),
        gate_error_cost=float(gate_cost),
        swap_cost_estimate=float(routing_cost),
        error_cost=float(readout_cost + gate_cost),
    )


def _infeasible(num_qpus: int) -> HypergraphMILPSolution:
    return HypergraphMILPSolution(
        "infeasible", num_qpus, None, (), (), (), None, None, None, None, None, None, None
    )
