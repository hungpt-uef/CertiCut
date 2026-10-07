from __future__ import annotations

from math import pi, sqrt

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, CZGate, DCXGate, iSwapGate, CSGate, RZZGate
from qiskit.quantum_info import Operator

from certicut.costs.qpd import qpd_cost


def test_manuscript_fixed_gate_qpd_costs_match_qiskit_registry() -> None:
    assert qpd_cost(CXGate()).overhead == pytest.approx(9.0)
    assert qpd_cost(CZGate()).overhead == pytest.approx(9.0)
    assert qpd_cost(iSwapGate()).overhead == pytest.approx(49.0)
    assert qpd_cost(DCXGate()).overhead == pytest.approx(49.0)
    assert qpd_cost(CSGate()).overhead == pytest.approx(3.0 + 2.0 * sqrt(2.0))


@pytest.mark.parametrize("theta", [pi / 8, pi / 4, pi / 2, -pi / 4])
def test_manuscript_rzz_qpd_formula_matches_qiskit_registry(theta: float) -> None:
    expected = (1.0 + 2.0 * abs(__import__("math").sin(theta))) ** 2
    assert qpd_cost(RZZGate(theta)).overhead == pytest.approx(expected)

def test_figure_one_numeric_witness_changes_balanced_optimum() -> None:
    low = qpd_cost(RZZGate(pi / 16)).log_cost
    cx = qpd_cost(CXGate()).log_cost
    native_cut_03_12 = 2.0 * low
    native_cut_01_23 = cx
    decomposed_cut_03_12 = 2.0 * cx + low
    decomposed_cut_01_23 = cx
    native_third = 2.0 * low + cx
    decomposed_third = 3.0 * cx + low
    assert native_cut_03_12 < native_cut_01_23 < native_third
    assert decomposed_cut_01_23 < decomposed_cut_03_12 < decomposed_third


def test_figure_one_rzz_decomposition_is_unitary_equivalent() -> None:
    theta = pi / 16
    direct = QuantumCircuit(2)
    direct.rzz(theta, 0, 1)
    decomposed = QuantumCircuit(2)
    decomposed.cx(0, 1)
    decomposed.rz(theta, 1)
    decomposed.cx(0, 1)
    assert Operator(direct).equiv(Operator(decomposed))
