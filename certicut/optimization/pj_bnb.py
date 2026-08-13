"""Certified anytime B&B for exact-balanced PJ-QPD using Lovasz objective cuts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
from itertools import combinations
from math import exp
from time import perf_counter
from typing import Mapping

import numpy as np
from qiskit import QuantumCircuit
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from certicut.optimization.certificate import Certificate, make_certificate
from certicut.optimization.parallel_joint import (
    ParallelLayerGate,
    evaluate_parallel_joint_partition,
    parallel_layer_gates,
)
from certicut.optimization.pj_lovasz import PJLovaszCut, make_pj_lovasz_cut


_TOL = 1e-9


@dataclass(frozen=True)
class PJNodeLPResult:
    status: str
    lower_bound: float | None
    z_values: tuple[float, ...] | None
    pair_values: dict[tuple[int, int], float] | None
    eta_values: tuple[float, ...] | None
    pj_separation_complete: bool
    separation_rounds: int
    geometry_pool_version: int
    pj_pool_version: int


@dataclass(frozen=True)
class PJTimelineEvent:
    expanded_nodes: int
    open_nodes: int
    global_lb: float
    incumbent_ub: float
    factor: float | None
    event: str
    pj_pool_version: int
    elapsed_s: float


@dataclass(frozen=True)
class PJCertifiedResult:
    status: str
    partition: tuple[int, ...]
    certificate: Certificate
    expanded_nodes: int
    pj_cuts_added: int
    geometry_cut_count: int
    timeline: tuple[PJTimelineEvent, ...]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class _Node:
    fixed: tuple[tuple[int, int], ...]
    lb: float
    z: tuple[float, ...]
    pj_complete: bool
    geometry_version: int
    pj_version: int


@dataclass
class GeometryCutPool:
    """Immutable exact-balance/cardinality/triangle geometry pool."""

    triangles: tuple[tuple[int, int, int, int], ...]
    version: int = 1


@dataclass
class ObjectiveCutPool:
    """Monotonic globally valid PJ Lovasz cuts, independently versioned."""

    cuts: dict[tuple[int, tuple[int, ...]], PJLovaszCut]
    version: int = 0

    def add(self, layer_id: int, cut: PJLovaszCut) -> bool:
        key = (layer_id, cut.instruction_order)
        if key in self.cuts:
            return False
        self.cuts[key] = cut
        self.version += 1
        return True


def _layer_groups(circuit: QuantumCircuit) -> tuple[tuple[ParallelLayerGate, ...], ...]:
    groups: dict[int, list[ParallelLayerGate]] = {}
    for gate in parallel_layer_gates(circuit):
        groups.setdefault(gate.layer, []).append(gate)
    return tuple(tuple(layer) for _, layer in sorted(groups.items()))


def _geometry_pool(n: int) -> GeometryCutPool:
    return GeometryCutPool(tuple((i, j, k, kind) for i, j, k in combinations(range(n), 3) for kind in range(4)))


def _solve_lp(
    circuit: QuantumCircuit,
    layers: tuple[tuple[ParallelLayerGate, ...], ...],
    geometry: GeometryCutPool,
    objective: ObjectiveCutPool,
    fixed: Mapping[int, int],
) -> PJNodeLPResult:
    """Solve B2S geometry plus a finite subset of globally valid PJ cuts."""
    n = circuit.num_qubits
    pairs = tuple(combinations(range(n), 2))
    pair_index = {pair: n + index for index, pair in enumerate(pairs)}
    gate_pair = {
        gate.instruction_index: tuple(sorted(gate.qubits))
        for layer in layers for gate in layer
    }
    eta_offset = n + len(pairs)
    variables = eta_offset + len(layers)
    # balance, 4 XOR envelope rows per pair, cardinality, triangles, PJ cuts.
    rows = 1 + 4 * len(pairs) + 1 + len(geometry.triangles) + len(objective.cuts)
    matrix = lil_matrix((rows, variables), dtype=float)
    lower = np.full(rows, -np.inf)
    upper = np.full(rows, np.inf)
    row = 0
    for q in range(n):
        matrix[row, q] = 1.0
    lower[row] = upper[row] = n / 2
    row += 1
    for u, v in pairs:
        x = pair_index[u, v]
        # x >= z_u-z_v; x >= z_v-z_u; x <= z_u+z_v; x <= 2-z_u-z_v.
        matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, -1.0, 1.0; lower[row] = 0.0; row += 1
        matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, 1.0, -1.0; lower[row] = 0.0; row += 1
        matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, -1.0, -1.0; upper[row] = 0.0; row += 1
        matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, 1.0, 1.0; upper[row] = 2.0; row += 1
    for pair in pairs:
        matrix[row, pair_index[pair]] = 1.0
    lower[row] = upper[row] = (n // 2) * (n // 2)
    row += 1
    for i, j, k, kind in geometry.triangles:
        ij, ik, jk = pair_index[i, j], pair_index[i, k], pair_index[j, k]
        if kind == 0:
            matrix[row, ij], matrix[row, ik], matrix[row, jk] = 1.0, -1.0, -1.0; upper[row] = 0.0
        elif kind == 1:
            matrix[row, ik], matrix[row, ij], matrix[row, jk] = 1.0, -1.0, -1.0; upper[row] = 0.0
        elif kind == 2:
            matrix[row, jk], matrix[row, ij], matrix[row, ik] = 1.0, -1.0, -1.0; upper[row] = 0.0
        else:
            matrix[row, ij], matrix[row, ik], matrix[row, jk] = 1.0, 1.0, 1.0; upper[row] = 2.0
        row += 1
    for (layer_id, _), cut in objective.cuts.items():
        matrix[row, eta_offset + layer_id] = 1.0
        for instruction, coefficient in zip(cut.instruction_order, cut.coefficients, strict=True):
            matrix[row, pair_index[gate_pair[instruction]]] -= coefficient
        lower[row] = 0.0
        row += 1
    assert row == rows
    costs = np.zeros(variables)
    costs[eta_offset:] = 1.0
    bounds = [(0.0, 1.0)] * (n + len(pairs)) + [(0.0, None)] * len(layers)
    bounds[0] = (0.0, 0.0)
    for qubit, side in fixed.items():
        bounds[qubit] = (float(side), float(side))
    # Convert >= lower rows to -A <= -lower, preserve <= rows. Equalities exist only balance/cardinality.
    eq_rows = [0, 1 + 4 * len(pairs)]
    ge_rows = [index for index in range(rows) if index not in eq_rows and np.isfinite(lower[index])]
    le_rows = [index for index in range(rows) if index not in eq_rows and np.isfinite(upper[index])]
    A_ub = lil_matrix((len(ge_rows) + len(le_rows), variables), dtype=float)
    b_ub = np.empty(len(ge_rows) + len(le_rows))
    for out, source in enumerate(ge_rows):
        A_ub[out, :] = -matrix[source, :]
        b_ub[out] = -lower[source]
    for offset, source in enumerate(le_rows, start=len(ge_rows)):
        A_ub[offset, :] = matrix[source, :]
        b_ub[offset] = upper[source]
    result = linprog(
        costs,
        A_ub=A_ub.tocsr() if len(ge_rows) + len(le_rows) else None,
        b_ub=b_ub if len(ge_rows) + len(le_rows) else None,
        A_eq=matrix[eq_rows, :].tocsr(), b_eq=lower[eq_rows],
        bounds=bounds, method="highs",
    )
    if result.status == 2:
        return PJNodeLPResult("infeasible", None, None, None, None, True, 0, geometry.version, objective.version)
    if result.status != 0 or result.x is None:
        raise RuntimeError(f"HiGHS PJ BnB LP failed: {result.status}: {result.message}")
    return PJNodeLPResult(
        "optimal", float(result.fun), tuple(float(result.x[q]) for q in range(n)),
        {pair: float(result.x[pair_index[pair]]) for pair in pairs},
        tuple(float(result.x[eta_offset + layer_id]) for layer_id in range(len(layers))),
        False, 0, geometry.version, objective.version,
    )


def _separate_node(
    circuit: QuantumCircuit,
    layers: tuple[tuple[ParallelLayerGate, ...], ...],
    geometry: GeometryCutPool,
    objective: ObjectiveCutPool,
    fixed: Mapping[int, int],
    max_rounds: int,
    deadline_at: float | None = None,
) -> PJNodeLPResult:
    """Complete PJ separation unless explicit round budget exhausts; each LP is safe."""
    latest: PJNodeLPResult | None = None
    for round_id in range(max_rounds + 1):
        latest = _solve_lp(circuit, layers, geometry, objective, fixed)
        if latest.status != "optimal" or latest.pair_values is None or latest.eta_values is None:
            return latest
        # A completed LP solve is a safe checkpoint even with incomplete cuts.
        if deadline_at is not None and perf_counter() >= deadline_at:
            return PJNodeLPResult(
                latest.status, latest.lower_bound, latest.z_values, latest.pair_values, latest.eta_values,
                False, round_id, geometry.version, latest.pj_pool_version,
            )
        additions = 0
        for layer_id, layer in enumerate(layers):
            values = [latest.pair_values[tuple(sorted(gate.qubits))] for gate in layer]
            cut = make_pj_lovasz_cut(layer, values)
            if latest.eta_values[layer_id] < cut.value_at_point - _TOL:
                additions += int(objective.add(layer_id, cut))
        if additions == 0:
            return PJNodeLPResult(
                latest.status, latest.lower_bound, latest.z_values, latest.pair_values, latest.eta_values,
                True, round_id, geometry.version, objective.version,
            )
        if deadline_at is not None and perf_counter() >= deadline_at:
            # `latest` was solved before just-added cuts, so retain its solved
            # pool version. It is weaker but remains a globally valid LB.
            return PJNodeLPResult(
                latest.status, latest.lower_bound, latest.z_values, latest.pair_values, latest.eta_values,
                False, round_id, geometry.version, latest.pj_pool_version,
            )
    assert latest is not None
    return PJNodeLPResult(
        latest.status, latest.lower_bound, latest.z_values, latest.pair_values, latest.eta_values,
        False, max_rounds, geometry.version, latest.pj_pool_version,
    )


def _integral(z: tuple[float, ...]) -> tuple[int, ...] | None:
    result = []
    for value in z:
        if abs(value) < _TOL:
            result.append(0)
        elif abs(value - 1.0) < _TOL:
            result.append(1)
        else:
            return None
    return tuple(result)


def _branch_qubit(z: tuple[float, ...], fixed: Mapping[int, int]) -> int:
    options = [(abs(value - 0.5), qubit) for qubit, value in enumerate(z) if qubit not in fixed and qubit != 0]
    if not options:
        raise RuntimeError("fractional PJ node has no branch candidate")
    return min(options)[1]


def _initial_partition(n: int) -> tuple[int, ...]:
    return tuple(0 if q < n // 2 else 1 for q in range(n))


def _global_lb(frontier: list[tuple[float, int, _Node]], ub: float) -> float:
    return min(ub, min((item[0] for item in frontier), default=ub))


def solve_certified_pj_bnb(
    circuit: QuantumCircuit,
    *,
    node_limit: int | None = None,
    time_limit_s: float | None = None,
    separation_round_limit: int = 100,
) -> PJCertifiedResult:
    """Best-bound safe-checkpoint PJ B&B with globally pooled Lovasz cuts."""
    n = circuit.num_qubits
    if n == 0 or n % 2:
        raise ValueError("PJ BnB requires positive even qubit count")
    start = perf_counter()
    deadline_at = start + time_limit_s if time_limit_s is not None else None
    layers = _layer_groups(circuit)
    geometry = _geometry_pool(n)
    objective = ObjectiveCutPool({})
    incumbent = _initial_partition(n)
    incumbent_ub = evaluate_parallel_joint_partition(circuit, incumbent).parallel_joint_log_cost
    root_lp = _separate_node(circuit, layers, geometry, objective, {0: 0}, separation_round_limit, deadline_at)
    if root_lp.status != "optimal" or root_lp.lower_bound is None or root_lp.z_values is None:
        raise RuntimeError("unexpected PJ root infeasibility")
    root = _Node(((0, 0),), root_lp.lower_bound, root_lp.z_values, root_lp.pj_separation_complete, geometry.version, objective.version)
    frontier: list[tuple[float, int, _Node]] = [(root.lb, 0, root)]
    sequence = 1
    expanded = 0
    timeline: list[PJTimelineEvent] = []

    def checkpoint(event: str) -> None:
        lb = _global_lb(frontier, incumbent_ub)
        certificate = make_certificate(lb, incumbent_ub)
        timeline.append(PJTimelineEvent(expanded, len(frontier), lb, incumbent_ub, certificate.overhead_factor_bound, event, objective.version, perf_counter() - start))

    checkpoint("root")
    if deadline_at is not None and perf_counter() >= deadline_at:
        lb = _global_lb(frontier, incumbent_ub)
        return PJCertifiedResult("time_limit", incumbent, make_certificate(lb, incumbent_ub), expanded, len(objective.cuts), len(geometry.triangles), tuple(timeline))
    while frontier:
        if node_limit is not None and expanded >= node_limit:
            lb = _global_lb(frontier, incumbent_ub)
            return PJCertifiedResult("node_limit", incumbent, make_certificate(lb, incumbent_ub), expanded, len(objective.cuts), len(geometry.triangles), tuple(timeline))
        if time_limit_s is not None and perf_counter() - start >= time_limit_s:
            lb = _global_lb(frontier, incumbent_ub)
            return PJCertifiedResult("time_limit", incumbent, make_certificate(lb, incumbent_ub), expanded, len(objective.cuts), len(geometry.triangles), tuple(timeline))
        _, _, node = heapq.heappop(frontier)
        # Stale bounds remain safe; reoptimization is for quality and integral exactness.
        if node.pj_version < objective.version or not node.pj_complete:
            refreshed = _separate_node(circuit, layers, geometry, objective, dict(node.fixed), separation_round_limit, deadline_at)
            if refreshed.status != "optimal" or refreshed.lower_bound is None or refreshed.z_values is None:
                expanded += 1
                checkpoint("infeasible")
                continue
            node = _Node(node.fixed, refreshed.lower_bound, refreshed.z_values, refreshed.pj_separation_complete, geometry.version, objective.version)
        if node.lb >= incumbent_ub - _TOL:
            expanded += 1
            checkpoint("prune")
            continue
        partition = _integral(node.z)
        if partition is not None:
            # Critical: an integral node may only be fathomed after complete PJ separation.
            if not node.pj_complete:
                heapq.heappush(frontier, (node.lb, sequence, node)); sequence += 1
                checkpoint("integral_unseparated")
                continue
            objective_value = evaluate_parallel_joint_partition(circuit, partition).parallel_joint_log_cost
            if objective_value < incumbent_ub - _TOL:
                incumbent, incumbent_ub = partition, objective_value
            expanded += 1
            checkpoint("integral")
            continue
        branch = _branch_qubit(node.z, dict(node.fixed))
        for side in (0, 1):
            fixed = (*node.fixed, (branch, side))
            child_lp = _separate_node(circuit, layers, geometry, objective, dict(fixed), separation_round_limit, deadline_at)
            if child_lp.status == "optimal" and child_lp.lower_bound is not None and child_lp.z_values is not None:
                child = _Node(fixed, child_lp.lower_bound, child_lp.z_values, child_lp.pj_separation_complete, geometry.version, objective.version)
                if child.lb < incumbent_ub - _TOL:
                    heapq.heappush(frontier, (child.lb, sequence, child)); sequence += 1
        expanded += 1
        checkpoint("branch")
    certificate = make_certificate(incumbent_ub, incumbent_ub)
    return PJCertifiedResult("optimal", incumbent, certificate, expanded, len(objective.cuts), len(geometry.triangles), tuple(timeline))
