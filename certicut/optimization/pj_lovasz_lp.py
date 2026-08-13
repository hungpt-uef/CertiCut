"""Cutting-plane LP relaxation for the layer-submodular PJ-QPD objective."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from certicut.optimization.parallel_joint import ParallelLayerGate, parallel_layer_gates
from certicut.optimization.pj_lovasz import PJLovaszCut, make_pj_lovasz_cut


@dataclass(frozen=True)
class PJLovaszRelaxationResult:
    status: str
    lower_bound_log: float | None
    assignments: tuple[float, ...] | None
    gate_cut_values: tuple[float, ...] | None
    layer_eta: tuple[float, ...] | None
    cuts: tuple[tuple[int, tuple[int, ...]], ...]
    separation_rounds: int
    variable_count: int
    constraint_count: int


def _layer_groups(circuit: QuantumCircuit) -> tuple[tuple[ParallelLayerGate, ...], ...]:
    groups: dict[int, list[ParallelLayerGate]] = {}
    for gate in parallel_layer_gates(circuit):
        groups.setdefault(gate.layer, []).append(gate)
    return tuple(tuple(group) for _, group in sorted(groups.items()))


def solve_pj_lovasz_relaxation(
    circuit: QuantumCircuit, *, tolerance: float = 1e-9, max_rounds: int = 100
) -> PJLovaszRelaxationResult:
    """Separate globally valid Lovasz epigraph cuts until the root LP converges.

    The LP is a certificate-safe lower relaxation: every selected greedy cut is
    valid for the convex Lovasz extension and agrees with PJ cost at binary x.
    """
    n = circuit.num_qubits
    if n == 0 or n % 2:
        raise ValueError("PJ Lovasz relaxation requires positive even qubit count")
    layers = _layer_groups(circuit)
    gates = tuple(gate for layer in layers for gate in layer)
    gate_to_index = {gate.instruction_index: i for i, gate in enumerate(gates)}
    z_count, x_count, eta_count = n, len(gates), len(layers)
    eta_offset = z_count + x_count
    variable_count = z_count + x_count + eta_count
    active: dict[tuple[int, tuple[int, ...]], PJLovaszCut] = {}
    for round_id in range(max_rounds + 1):
        # balance + two XOR lower bounds per gate + active epigraph cuts
        rows = 1 + 2 * x_count + len(active)
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
        for (layer_id, _), cut in active.items():
            matrix[row, eta_offset + layer_id] = 1.0
            for instruction, coefficient in zip(cut.instruction_order, cut.coefficients, strict=True):
                matrix[row, z_count + gate_to_index[instruction]] -= coefficient
            lower[row] = 0.0
            row += 1
        costs = np.zeros(variable_count)
        costs[eta_offset:] = 1.0
        bounds = [(0.0, 1.0)] * (z_count + x_count) + [(0.0, None)] * eta_count
        bounds[0] = (0.0, 0.0)
        # SciPy linprog needs lower/upper matrix represented by A_ub. Convert.
        # All rows here are equality or >=. Split after construction for clarity.
        eq_rows = [0]
        ge_rows = list(range(1, rows))
        result = linprog(
            costs,
            A_ub=(-matrix[ge_rows, :]).tocsr() if ge_rows else None,
            b_ub=(-lower[ge_rows]) if ge_rows else None,
            A_eq=matrix[eq_rows, :].tocsr(),
            b_eq=lower[eq_rows],
            bounds=bounds,
            method="highs",
        )
        if result.status == 2:
            return PJLovaszRelaxationResult("infeasible", None, None, None, None, tuple(active), round_id, variable_count, rows)
        if result.status != 0 or result.x is None:
            raise RuntimeError(f"HiGHS PJ Lovasz LP failed: {result.status}: {result.message}")
        x_values = tuple(float(result.x[z_count + i]) for i in range(x_count))
        eta = tuple(float(result.x[eta_offset + i]) for i in range(eta_count))
        additions = 0
        for layer_id, layer in enumerate(layers):
            values = [x_values[gate_to_index[gate.instruction_index]] for gate in layer]
            cut = make_pj_lovasz_cut(layer, values)
            key = (layer_id, cut.instruction_order)
            if eta[layer_id] < cut.value_at_point - tolerance and key not in active:
                active[key] = cut
                additions += 1
        if additions == 0:
            return PJLovaszRelaxationResult(
                "optimal", float(result.fun), tuple(float(result.x[q]) for q in range(n)), x_values,
                eta, tuple(active), round_id, variable_count, rows,
            )
    raise RuntimeError("PJ Lovasz separation reached max_rounds")
