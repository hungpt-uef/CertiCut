"""Semantic boundary tests for executable independent and surrogate joint costs."""

from cmath import exp
from math import isclose, log, pi

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit.circuit.library import CXGate, CZGate, RZZGate, iSwapGate

from certicut.costs.joint_qpd import (
    JointQPDMode,
    joint_cost_oracle,
    schmitt_parallel_applicability,
    schmitt_parallel_cost,
)
from certicut.costs.qpd import qpd_cost
from certicut.costs.joint_parallel import build_schmitt_parallel_decomposition
from certicut.qiskit_bridge.joint_parallel import (
    build_interference_instrument_circuit,
    reconstruct_parallel_joint_expectations,
)


def test_independent_oracle_equals_product_of_crossed_qpd_overheads():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.append(iSwapGate(), [1, 2])

    estimate = joint_cost_oracle(JointQPDMode.INDEPENDENT_QPD, circuit, (0, 1), (0,))

    assert estimate.executable
    assert estimate.decomposition_available
    assert estimate.theorem_status == "exact_independent"
    assert isclose(estimate.log_overhead or 0.0, log(9), abs_tol=1e-12)
    assert isclose(estimate.overhead or 0.0, 9.0, abs_tol=1e-12)
    assert estimate.metadata["crossed_gate_indices"] == (0,)


def test_schmidt_surrogate_is_never_marked_executable_joint_qpd():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(1, 2)

    estimate = joint_cost_oracle("schmidt_surrogate", circuit, (0, 1), (0,))

    assert estimate.log_overhead == log(2)
    assert estimate.executable is False
    assert estimate.decomposition_available is False
    assert estimate.theorem_status == "surrogate_only"


def test_theoretical_joint_mode_fails_closed_without_construction():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(1, 2)

    estimate = joint_cost_oracle("theoretical_joint_qpd", circuit, (0, 1), (0,))

    assert estimate.log_overhead is None
    assert estimate.overhead is None
    assert estimate.executable is False
    assert estimate.theorem_status == "unimplemented_theory"


def test_weak_rzz_reverses_schmidt_and_independent_cost_ordering():
    circuit = QuantumCircuit(2)
    circuit.rzz(0.1, 0, 1)

    independent = joint_cost_oracle("independent_qpd", circuit, (0,), (0,))
    surrogate = joint_cost_oracle("schmidt_surrogate", circuit, (0,), (0,))

    assert surrogate.log_overhead == log(2)
    assert (independent.log_overhead or 0.0) < surrogate.log_overhead


def test_schmitt_single_gate_reduction_matches_qiskit_qpd_overhead():
    for operation in (CXGate(), CZGate(), RZZGate(pi / 4), iSwapGate()):
        circuit = QuantumCircuit(2)
        circuit.append(operation, (0, 1))
        result = schmitt_parallel_cost(circuit, (0,), (0,))

        assert result.applicability.applicable
        assert not result.executable
        assert not result.decomposition_available
        assert isclose(result.sampling_overhead or 0.0, qpd_cost(operation).overhead, abs_tol=1e-10)
        assert isclose(result.log_sampling_overhead or 0.0, qpd_cost(operation).log_cost, abs_tol=1e-10)


def test_schmitt_parallel_cx_pair_has_strict_joint_advantage():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)

    result = schmitt_parallel_cost(circuit, (0, 1), (0, 1))

    assert result.applicability.applicable
    assert result.applicability.parallel_tensor_product_verified
    assert isclose(result.coefficient_l1_norm or 0.0, 7.0, abs_tol=1e-10)
    assert isclose(result.sampling_overhead or 0.0, 49.0, abs_tol=1e-10)
    assert (result.sampling_overhead or 0.0) < 9.0**2


def test_schmitt_parallel_checker_fails_closed_for_temporal_overlap():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(1, 2)

    eligibility = schmitt_parallel_applicability(circuit, (0, 1), (0, 2))
    result = schmitt_parallel_cost(circuit, (0, 1), (0, 2))

    assert not eligibility.applicable
    assert "common circuit layer" in eligibility.reason
    assert result.sampling_overhead is None


def test_schmitt_parallel_checker_rejects_interleaved_local_operation():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.x(0)
    circuit.cx(1, 3)

    eligibility = schmitt_parallel_applicability(circuit, (0, 2), (0, 1))

    assert not eligibility.applicable
    assert not eligibility.parallel_tensor_product_verified
    assert "interleaved" in eligibility.reason


def test_parallel_cx_decomposition_has_n_squared_terms_and_exact_channel():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)

    decomposition = build_schmitt_parallel_decomposition(circuit, (0, 1), (0, 1))

    assert len(decomposition.composite_kak_terms) == 4
    assert len(decomposition.qpd_terms) == 16
    assert isclose(decomposition.coefficient_l1_norm, 7.0, abs_tol=1e-10)
    assert isclose(decomposition.sampling_overhead, 49.0, abs_tol=1e-10)
    assert decomposition.composite_kak_reconstruction_error < 1e-12
    assert decomposition.algebraically_verified
    assert (decomposition.algebraic_reconstruction_error or 1.0) < 1e-10
    assert decomposition.operationally_executable is False
    for term in decomposition.qpd_terms:
        if term.term_type == "interference":
            assert term.instrument_a.ancilla_requirement == term.instrument_b.ancilla_requirement == 1
            assert term.instrument_a.cptp_branch_sum_error() < 1e-10
            assert term.instrument_b.cptp_branch_sum_error() < 1e-10


def test_three_parallel_cx_has_n_squared_outer_term_structure():
    circuit = QuantumCircuit(6)
    circuit.cx(0, 3)
    circuit.cx(1, 4)
    circuit.cx(2, 5)

    decomposition = build_schmitt_parallel_decomposition(circuit, (0, 1, 2), (0, 1, 2))

    assert len(decomposition.composite_kak_terms) == 8
    assert len(decomposition.qpd_terms) == 64
    assert isclose(decomposition.coefficient_l1_norm, 15.0, abs_tol=1e-10)
    assert isclose(decomposition.sampling_overhead, 225.0, abs_tol=1e-10)
    assert decomposition.algebraically_verified is False


def test_two_parallel_iswap_has_theorem_norm_and_overhead():
    circuit = QuantumCircuit(4)
    circuit.append(iSwapGate(), (0, 2))
    circuit.append(iSwapGate(), (1, 3))

    decomposition = build_schmitt_parallel_decomposition(circuit, (0, 1), (0, 1))

    assert len(decomposition.composite_kak_terms) == 16
    assert len(decomposition.qpd_terms) == 256
    assert isclose(decomposition.coefficient_l1_norm, 31.0, abs_tol=1e-10)
    assert isclose(decomposition.sampling_overhead, 961.0, abs_tol=1e-10)
    assert decomposition.composite_kak_reconstruction_error < 1e-12
    assert decomposition.algebraically_verified


def test_global_phase_preserves_parallel_cost_and_channel_semantics():
    reference = QuantumCircuit(2)
    reference.cx(0, 1)
    phased = QuantumCircuit(2)
    phased.append(UnitaryGate(exp(0.371j) * CXGate().to_matrix()), (0, 1))

    original = build_schmitt_parallel_decomposition(reference, (0,), (0,))
    shifted = build_schmitt_parallel_decomposition(phased, (0,), (0,))

    assert isclose(original.coefficient_l1_norm, shifted.coefficient_l1_norm, abs_tol=1e-10)
    assert isclose(original.sampling_overhead, shifted.sampling_overhead, abs_tol=1e-10)
    assert (shifted.algebraic_reconstruction_error or 1.0) < 1e-10


def test_ancilla_multiplexor_matches_signed_instrument_kraus_operators():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    decomposition = build_schmitt_parallel_decomposition(circuit, (0,), (0,))
    term = next(term for term in decomposition.qpd_terms if term.term_type == "interference")

    bridge_a = build_interference_instrument_circuit(term.instrument_a, term.theta or 0.0)
    bridge_b = build_interference_instrument_circuit(term.instrument_b, term.theta or 0.0)

    assert bridge_a.zero_error < 1e-12
    assert bridge_a.one_error < 1e-12
    assert bridge_b.zero_error < 1e-12
    assert bridge_b.one_error < 1e-12


def test_exact_joint_reconstruction_matches_multiple_pauli_observables():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.append(RZZGate(pi / 4), (1, 3))
    decomposition = build_schmitt_parallel_decomposition(circuit, (0, 1), (0, 1))
    zero = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
    plus = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
    rho_a = np.kron(plus, zero)
    rho_b = np.kron(zero, plus)
    x = np.array([[0.0, 1.0], [1.0, 0.0]])
    y = np.array([[0.0, -1j], [1j, 0.0]])
    z = np.diag([1.0, -1.0])
    identity = np.eye(2)
    observables = (
        (np.kron(z, z), np.kron(z, z)),
        (np.kron(x, identity), np.kron(x, identity)),
        (np.kron(y, identity), np.kron(z, y)),
        (np.kron(x, z), np.kron(y, x)),
    )

    result = reconstruct_parallel_joint_expectations(decomposition, rho_a, rho_b, observables)

    assert result.operationally_executable
    assert result.max_observable_error < 1e-10
    assert isclose(result.generated_gamma, decomposition.coefficient_l1_norm, abs_tol=1e-12)
    assert isclose(result.generated_overhead, decomposition.sampling_overhead, abs_tol=1e-12)
    assert result.ancilla_qubits_a == result.ancilla_qubits_b == 1


def test_joint_reconstruction_fails_closed_when_ancilla_width_does_not_fit():
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    decomposition = build_schmitt_parallel_decomposition(circuit, (0,), (0,))
    rho = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)

    result = reconstruct_parallel_joint_expectations(
        decomposition, rho, rho, ((np.diag([1.0, -1.0]), np.diag([1.0, -1.0])),),
        available_width_a=1, available_width_b=1,
    )

    assert not result.operationally_executable
    assert result.reason == "ancilla_capacity"


def test_two_parallel_cx_operationally_realizes_gamma_squared_49():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)
    decomposition = build_schmitt_parallel_decomposition(circuit, (0, 1), (0, 1))
    plus = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=complex)
    zero = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=complex)
    rho_a = np.kron(plus, zero)
    rho_b = np.kron(zero, plus)
    x = np.array([[0.0, 1.0], [1.0, 0.0]])
    z = np.diag([1.0, -1.0])

    result = reconstruct_parallel_joint_expectations(
        decomposition, rho_a, rho_b, ((np.kron(x, z), np.kron(z, x)),)
    )

    assert result.operationally_executable
    assert isclose(result.generated_overhead, 49.0, abs_tol=1e-12)
    assert result.max_observable_error < 1e-10
