"""Independent exact MILP and brute-force oracles for balanced PJ-QPD partitioning."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from math import exp
from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from certicut.optimization.parallel_joint import (
    ParallelLayerGate,
    evaluate_parallel_joint_partition,
    parallel_layer_gates,
    pj_layer_function,
)


@dataclass(frozen=True)
class PJExactSolution:
    status: str
    partition: tuple[int, ...] | None
    objective_log_cost: float | None
    overhead: float | None
    cut_gate_count: int
    crossed_by_layer: tuple[tuple[int, ...], ...]
    variable_count: int
    constraint_count: int

    def as_dict(self) -> dict:
        return asdict(self)


def _layer_groups(circuit: QuantumCircuit) -> tuple[tuple[ParallelLayerGate, ...], ...]:
    grouped: dict[int, list[ParallelLayerGate]] = {}
    for gate in parallel_layer_gates(circuit):
        grouped.setdefault(gate.layer, []).append(gate)
    return tuple(tuple(gates) for _, gates in sorted(grouped.items()))


def solve_exact_pj_pattern_milp(circuit: QuantumCircuit, *, time_limit_s: float | None = None) -> PJExactSolution:
    """Solve exact balanced K=2 PJ-QPD with one binary pattern per circuit layer.

    This oracle is intentionally exponential in layer width. It validates small
    instances and generic HiGHS behavior; it is not the scalable CertiCut solver.
    """
    n = circuit.num_qubits
    if n == 0 or n % 2:
        raise ValueError("exact PJ oracle requires a positive even qubit count")
    layers = _layer_groups(circuit)
    gates = tuple(gate for layer in layers for gate in layer)
    gate_index = {gate.instruction_index: index for index, gate in enumerate(gates)}
    z_count, x_count = n, len(gates)
    patterns = {
        layer_id: tuple(range(1 << len(layer)))
        for layer_id, layer in enumerate(layers)
    }
    offset = z_count + x_count
    h_index: dict[tuple[int, int], int] = {}
    objective: list[float] = [0.0] * offset
    for layer_id, layer in enumerate(layers):
        for pattern in patterns[layer_id]:
            h_index[layer_id, pattern] = len(objective)
            total = sum(gate.log_s for bit, gate in enumerate(layer) if pattern & (1 << bit))
            objective.append(pj_layer_function(total))
    variable_count = len(objective)

    # balance equality; XOR (two per gate); one pattern per layer; pattern-to-x equality.
    rows = 1 + 2 * x_count + len(layers) + x_count
    matrix = lil_matrix((rows, variable_count), dtype=float)
    lower = np.full(rows, -np.inf)
    upper = np.full(rows, np.inf)
    row = 0
    for qubit in range(n):
        matrix[row, qubit] = 1.0
    lower[row] = upper[row] = n / 2
    row += 1
    for gate_id, gate in enumerate(gates):
        x = z_count + gate_id
        u, v = gate.qubits
        matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, -1.0, 1.0
        lower[row] = 0.0
        row += 1
        matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, 1.0, -1.0
        lower[row] = 0.0
        row += 1
    for layer_id, layer in enumerate(layers):
        for pattern in patterns[layer_id]:
            matrix[row, h_index[layer_id, pattern]] = 1.0
        lower[row] = upper[row] = 1.0
        row += 1
        for bit, gate in enumerate(layer):
            x = z_count + gate_index[gate.instruction_index]
            matrix[row, x] = -1.0
            for pattern in patterns[layer_id]:
                if pattern & (1 << bit):
                    matrix[row, h_index[layer_id, pattern]] += 1.0
            lower[row] = upper[row] = 0.0
            row += 1
    assert row == rows
    bounds = Bounds(np.zeros(variable_count), np.ones(variable_count))
    bounds.lb[0] = bounds.ub[0] = 0.0
    if time_limit_s is not None and time_limit_s < 0:
        raise ValueError("time_limit_s must be nonnegative")
    result = milp(
        c=np.asarray(objective),
        integrality=np.ones(variable_count),
        bounds=bounds,
        constraints=LinearConstraint(matrix.tocsr(), lower, upper),
        options={"disp": False, **({"time_limit": time_limit_s} if time_limit_s is not None else {})},
    )
    if result.status == 2 or result.x is None:
        return PJExactSolution("infeasible", None, None, None, 0, (), variable_count, rows)
    if result.status == 1:
        if result.x is None:
            return PJExactSolution("time_limit", None, None, None, 0, (), variable_count, rows)
        partition = tuple(int(result.x[qubit] > 0.5) for qubit in range(n))
        evaluation = evaluate_parallel_joint_partition(circuit, partition)
        return PJExactSolution(
            "time_limit", partition, evaluation.parallel_joint_log_cost, evaluation.parallel_joint_overhead,
            evaluation.cut_gate_count, evaluation.crossed_by_layer, variable_count, rows,
        )
    if result.status != 0:
        raise RuntimeError(f"HiGHS PJ pattern MILP failed: {result.status}: {result.message}")
    partition = tuple(int(result.x[qubit] > 0.5) for qubit in range(n))
    evaluation = evaluate_parallel_joint_partition(circuit, partition)
    return PJExactSolution(
        "optimal", partition, evaluation.parallel_joint_log_cost, evaluation.parallel_joint_overhead,
        evaluation.cut_gate_count, evaluation.crossed_by_layer, variable_count, rows,
    )


def brute_force_exact_pj(circuit: QuantumCircuit) -> PJExactSolution:
    """Symmetry-reduced exact-balanced oracle independent from pattern MILP."""
    n = circuit.num_qubits
    if n == 0 or n % 2:
        raise ValueError("exact PJ oracle requires a positive even qubit count")
    best_partition: tuple[int, ...] | None = None
    best = None
    for zero_rest in combinations(range(1, n), n // 2 - 1):
        partition = tuple(0 if qubit in (0, *zero_rest) else 1 for qubit in range(n))
        evaluation = evaluate_parallel_joint_partition(circuit, partition)
        if best is None or evaluation.parallel_joint_log_cost < best.parallel_joint_log_cost - 1e-12:
            best_partition, best = partition, evaluation
    assert best_partition is not None and best is not None
    return PJExactSolution(
        "optimal", best_partition, best.parallel_joint_log_cost, best.parallel_joint_overhead,
        best.cut_gate_count, best.crossed_by_layer, 0, 0,
    )
