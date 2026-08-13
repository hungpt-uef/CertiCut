"""Algebraic Schmitt--Piveteau--Sutter parallel joint-QPD decomposition.

Restricted to Corollary 4.1: pairwise-disjoint numeric two-qubit unitaries
crossing a fixed bipartition. This module validates an algebraic decomposition;
it does not yet build ancilla circuits or claim operational executability.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import log
from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from qiskit.synthesis import TwoQubitWeylDecomposition
from scipy.linalg import expm

from certicut.costs.joint_qpd import JointQPDOracleUnsupported, schmitt_parallel_applicability


PAULIS = (
    np.eye(2, dtype=complex),
    np.array([[0, 1], [1, 0]], dtype=complex),
    np.array([[0, -1j], [1j, 0]], dtype=complex),
    np.array([[1, 0], [0, -1]], dtype=complex),
)


@dataclass(frozen=True)
class KAKGateTerm:
    """Full two-qubit KAK data, including complex central coefficients."""

    instruction_index: int
    coefficient: tuple[complex, ...]
    pre_a: np.ndarray
    pre_b: np.ndarray
    post_a: np.ndarray
    post_b: np.ndarray
    global_phase: float
    reconstruction_error: float


@dataclass(frozen=True)
class CompositeKAKTerm:
    """One Pauli-string tensor-product term in the parallel KAK expansion."""

    multi_index: tuple[int, ...]
    coefficient: complex
    left_operator: np.ndarray
    right_operator: np.ndarray


@dataclass(frozen=True)
class LocalSignedInstrument:
    """Signed local map represented by CP Kraus branches and postprocessing signs."""

    branch_operators: tuple[np.ndarray, ...]
    branch_signs: tuple[int, ...]
    ancilla_requirement: int

    def superoperator(self) -> np.ndarray:
        return sum(
            sign * _superoperator(operator)
            for operator, sign in zip(self.branch_operators, self.branch_signs, strict=True)
        )

    def cptp_branch_sum_error(self) -> float:
        identity = np.eye(self.branch_operators[0].shape[1], dtype=complex)
        return float(np.linalg.norm(sum(op.conj().T @ op for op in self.branch_operators) - identity))


@dataclass(frozen=True)
class JointOuterQPDTerm:
    """One outer real-coefficient term of Lemma 5.2's QPD construction."""

    term_type: str
    outer_coefficient_real: float
    multi_index: tuple[int, ...]
    multi_index_prime: tuple[int, ...] | None
    theta: float | None
    instrument_a: LocalSignedInstrument
    instrument_b: LocalSignedInstrument


@dataclass(frozen=True)
class JointParallelDecomposition:
    """Theorem-backed algebraic decomposition; operational execution remains false."""

    theorem_id: str
    partition_a: tuple[int, ...]
    kak_terms: tuple[KAKGateTerm, ...]
    composite_kak_terms: tuple[CompositeKAKTerm, ...]
    qpd_terms: tuple[JointOuterQPDTerm, ...]
    coefficient_l1_norm: float
    sampling_overhead: float
    log_sampling_overhead: float
    target_unitary: np.ndarray
    composite_kak_reconstruction_error: float
    algebraic_reconstruction_error: float | None
    algebraically_verified: bool
    operationally_executable: bool


def _tensor(operators: Sequence[np.ndarray]) -> np.ndarray:
    result = np.array([[1.0 + 0.0j]])
    for operator in operators:
        result = np.kron(result, operator)
    return result


def _superoperator(operator: np.ndarray) -> np.ndarray:
    return np.kron(operator.conj(), operator)


def _product_instrument_superoperator(
    instrument_a: LocalSignedInstrument, instrument_b: LocalSignedInstrument
) -> np.ndarray:
    """Build the product map branchwise; avoids vectorization tensor-order ambiguity."""
    return sum(
        sign_a * sign_b * _superoperator(np.kron(operator_a, operator_b))
        for operator_a, sign_a in zip(instrument_a.branch_operators, instrument_a.branch_signs, strict=True)
        for operator_b, sign_b in zip(instrument_b.branch_operators, instrument_b.branch_signs, strict=True)
    )


def _phase_invariant_error(actual: np.ndarray, reconstructed: np.ndarray) -> float:
    overlap = np.trace(actual.conj().T @ reconstructed)
    phase = 1.0 if abs(overlap) < 1e-15 else np.exp(-1j * np.angle(overlap))
    return float(np.linalg.norm(actual - phase * reconstructed))


def _parallel_circuit_unitary_in_partition_basis(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> np.ndarray:
    """Return the selected parallel block unitary in ordered A_1..A_n,B_1..B_n basis."""
    side_a = set(partition_a)
    support = tuple(sorted({circuit.find_bit(q).index for index in gate_indices for q in circuit.data[index].qubits}))
    local = QuantumCircuit(len(support))
    mapping = {qubit: position for position, qubit in enumerate(support)}
    ordered_a: list[int] = []
    ordered_b: list[int] = []
    for index in gate_indices:
        instruction = circuit.data[index]
        logical = [circuit.find_bit(q).index for q in instruction.qubits]
        local.append(instruction.operation, [mapping[q] for q in logical])
        ordered_a.append(next(q for q in logical if q in side_a))
        ordered_b.append(next(q for q in logical if q not in side_a))
    factor_order = ordered_a + ordered_b
    dimension = 2 ** len(support)
    permutation = np.zeros((dimension, dimension), dtype=complex)
    for target_index in range(dimension):
        bits = [(target_index >> (len(support) - 1 - offset)) & 1 for offset in range(len(support))]
        # `bits` follows the Kronecker convention (first factor is MSB), while
        # Qiskit circuit qubit 0 is the least-significant matrix bit.
        qiskit_index = sum(
            bit << mapping[qubit] for bit, qubit in zip(bits, factor_order, strict=True)
        )
        permutation[qiskit_index, target_index] = 1.0
    return permutation.conj().T @ Operator(local).data @ permutation


def _weyl_gate_term(instruction_index: int, operation: object, a_on_first_operand: bool) -> KAKGateTerm:
    unitary = Operator(operation).data
    decomposition = TwoQubitWeylDecomposition(unitary, fidelity=None)
    exponent = 1j * (
        decomposition.a * np.kron(PAULIS[1], PAULIS[1])
        + decomposition.b * np.kron(PAULIS[2], PAULIS[2])
        + decomposition.c * np.kron(PAULIS[3], PAULIS[3])
    )
    central = expm(exponent)
    coefficients = tuple(
        complex(np.trace(np.kron(pauli, pauli).conj().T @ central) / 4.0)
        for pauli in PAULIS
    )
    reconstructed = (
        np.exp(1j * decomposition.global_phase)
        * np.kron(decomposition.K1l, decomposition.K1r)
        @ central
        @ np.kron(decomposition.K2l, decomposition.K2r)
    )
    error = _phase_invariant_error(unitary, reconstructed)
    if error >= 1e-12:
        raise JointQPDOracleUnsupported(
            f"Weyl reconstruction error for instruction {instruction_index} is {error:.3e}"
        )
    if a_on_first_operand:
        # Qiskit two-qubit matrix tensor order is second operand (left factor),
        # then first operand (right factor).
        pre_a, pre_b = decomposition.K2r, decomposition.K2l
        post_a, post_b = decomposition.K1r, decomposition.K1l
    else:
        pre_a, pre_b = decomposition.K2l, decomposition.K2r
        post_a, post_b = decomposition.K1l, decomposition.K1r
    return KAKGateTerm(
        instruction_index, coefficients, pre_a, pre_b, post_a, post_b,
        float(decomposition.global_phase), error,
    )


def _composite_kak_terms(kak_terms: Sequence[KAKGateTerm]) -> tuple[CompositeKAKTerm, ...]:
    terms: list[CompositeKAKTerm] = []
    for multi_index in product(range(4), repeat=len(kak_terms)):
        coefficient = complex(np.prod([term.coefficient[index] for term, index in zip(kak_terms, multi_index, strict=True)]))
        if abs(coefficient) <= 1e-10:
            continue
        terms.append(
            CompositeKAKTerm(
                multi_index,
                coefficient,
                _tensor([PAULIS[index] for index in multi_index]),
                _tensor([PAULIS[index] for index in multi_index]),
            )
        )
    return tuple(terms)


def _wrap_instrument(
    operators: Sequence[np.ndarray], signs: Sequence[int], post: np.ndarray, pre: np.ndarray, ancillas: int
) -> LocalSignedInstrument:
    return LocalSignedInstrument(
        tuple(post @ operator @ pre for operator in operators), tuple(signs), ancillas
    )


def build_schmitt_parallel_decomposition(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> JointParallelDecomposition:
    """Generate Lemma 5.2 outer QPD terms for the exact parallel theorem class.

    This builds the algebraic signed-instrument identity. It does not map the
    instruments to ancilla circuits, so `operationally_executable` stays false.
    """
    applicability = schmitt_parallel_applicability(circuit, gate_indices, partition_a)
    if not applicability.applicable:
        raise JointQPDOracleUnsupported(applicability.reason)
    side_a = set(partition_a)
    kak_terms = tuple(
        _weyl_gate_term(
            index,
            circuit.data[index].operation,
            circuit.find_bit(circuit.data[index].qubits[0]).index in side_a,
        )
        for index in applicability.gate_indices
    )
    composite = _composite_kak_terms(kak_terms)
    pre_a, pre_b = _tensor([term.pre_a for term in kak_terms]), _tensor([term.pre_b for term in kak_terms])
    post_a, post_b = _tensor([term.post_a for term in kak_terms]), _tensor([term.post_b for term in kak_terms])
    outer_terms: list[JointOuterQPDTerm] = []
    for term in composite:
        instrument_a = _wrap_instrument((term.left_operator,), (1,), post_a, pre_a, 0)
        instrument_b = _wrap_instrument((term.right_operator,), (1,), post_b, pre_b, 0)
        outer_terms.append(JointOuterQPDTerm("diagonal", abs(term.coefficient) ** 2, term.multi_index, None, None, instrument_a, instrument_b))
    for left_position, left in enumerate(composite):
        for right in composite[left_position + 1:]:
            phase = float(np.angle(left.coefficient) - np.angle(right.coefficient))
            magnitude = 2.0 * abs(left.coefficient) * abs(right.coefficient)
            for theta, sign in ((phase / 2.0, 1.0), (phase / 2.0 + np.pi / 2.0, -1.0)):
                left_plus = (left.left_operator + np.exp(-1j * theta) * right.left_operator) / 2.0
                left_minus = (left.left_operator - np.exp(-1j * theta) * right.left_operator) / 2.0
                right_plus = (left.right_operator + np.exp(-1j * theta) * right.right_operator) / 2.0
                right_minus = (left.right_operator - np.exp(-1j * theta) * right.right_operator) / 2.0
                outer_terms.append(
                    JointOuterQPDTerm(
                        "interference", sign * magnitude, left.multi_index, right.multi_index, theta,
                        _wrap_instrument((left_plus, left_minus), (1, -1), post_a, pre_a, 1),
                        _wrap_instrument((right_plus, right_minus), (1, -1), post_b, pre_b, 1),
                    )
                )
    coefficient_l1 = float(sum(abs(term.outer_coefficient_real) for term in outer_terms))
    target_central = sum(np.kron(term.left_operator, term.right_operator) * term.coefficient for term in composite)
    target = np.kron(post_a, post_b) @ target_central @ np.kron(pre_a, pre_b)
    composite_error = _phase_invariant_error(
        _parallel_circuit_unitary_in_partition_basis(circuit, applicability.gate_indices, partition_a), target
    )
    if composite_error >= 1e-12:
        raise JointQPDOracleUnsupported(f"parallel KAK reconstruction error is {composite_error:.3e}")
    # A global phase does not change a unitary channel.
    algebraic_error: float | None = None
    verified = False
    if len(kak_terms) <= 2:
        reconstructed_channel = sum(
            term.outer_coefficient_real * _product_instrument_superoperator(term.instrument_a, term.instrument_b)
            for term in outer_terms
        )
        algebraic_error = float(np.linalg.norm(_superoperator(target) - reconstructed_channel))
        verified = algebraic_error < 1e-10
    return JointParallelDecomposition(
        "schmitt2025_lemma_5_2_corollary_4_1_parallel",
        tuple(sorted(partition_a)),
        kak_terms,
        composite,
        tuple(outer_terms),
        coefficient_l1,
        coefficient_l1 * coefficient_l1,
        2.0 * log(coefficient_l1),
        target,
        composite_error,
        algebraic_error,
        verified,
        False,
    )
