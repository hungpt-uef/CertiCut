"""Exact operational bridge for theorem-backed parallel joint-QPD instruments.

It intentionally does not use Qiskit Addon Cutting's QPDBasis because parallel
joint terms are correlated signed instruments. Exact branch enumeration only.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import UnitaryGate
from qiskit.quantum_info import Operator

from certicut.costs.joint_parallel import JointParallelDecomposition, LocalSignedInstrument


@dataclass(frozen=True)
class AncillaInstrumentCircuit:
    """Direct ancilla realization of a canonical two-branch signed instrument."""

    circuit: QuantumCircuit
    kraus_zero: np.ndarray
    kraus_one: np.ndarray
    zero_error: float
    one_error: float


@dataclass(frozen=True)
class JointReconstructionResult:
    """Exact reconstruction evidence for one decomposition in local circuit context."""

    generated_gamma: float
    generated_overhead: float
    theorem_gamma: float
    theorem_overhead: float
    observable_errors: tuple[float, ...]
    max_observable_error: float
    required_width_a: int
    required_width_b: int
    ancilla_qubits_a: int
    ancilla_qubits_b: int
    operationally_executable: bool
    reason: str | None


def _conditional_kraus(unitary: np.ndarray, data_dimension: int, outcome: int) -> np.ndarray:
    """Extract <outcome|U|0> when ancilla is the most-significant basis factor."""
    return unitary[outcome * data_dimension : (outcome + 1) * data_dimension, :data_dimension]


def build_interference_instrument_circuit(
    instrument: LocalSignedInstrument, theta: float
) -> AncillaInstrumentCircuit:
    """Generate H--multiplexor--H circuit retaining the controlled relative phase."""
    if len(instrument.branch_operators) != 2 or instrument.branch_signs != (1, -1):
        raise ValueError("interference bridge requires the canonical two-branch signed instrument")
    plus, minus = instrument.branch_operators
    dimension = plus.shape[0]
    if plus.shape != minus.shape or plus.shape[0] != plus.shape[1]:
        raise ValueError("instrument branch matrices must be square and same-sized")
    # K+ and K- already contain the theorem's relative phase. Therefore
    # M = |0><0| (K+ + K-) + |1><1| (K+ - K-); adding theta again here
    # would make a controlled global phase physically observable and wrong.
    first = plus + minus
    second = plus - minus
    multiplexor = np.block([[first, np.zeros_like(first)], [np.zeros_like(second), second]])
    data_qubits = int(round(np.log2(dimension)))
    circuit = QuantumCircuit(data_qubits + 1, 1)
    ancilla = data_qubits
    circuit.h(ancilla)
    circuit.append(UnitaryGate(multiplexor), tuple(range(data_qubits + 1)))
    circuit.h(ancilla)
    unitary = Operator(circuit.remove_final_measurements(inplace=False)).data
    zero = _conditional_kraus(unitary, dimension, 0)
    one = _conditional_kraus(unitary, dimension, 1)
    return AncillaInstrumentCircuit(
        circuit, zero, one, float(np.linalg.norm(zero - plus)), float(np.linalg.norm(one - minus))
    )


def _signed_expectation(instrument: LocalSignedInstrument, rho: np.ndarray, observable: np.ndarray) -> complex:
    return sum(
        sign * np.trace(observable @ branch @ rho @ branch.conj().T)
        for branch, sign in zip(instrument.branch_operators, instrument.branch_signs, strict=True)
    )


def _target_expectation(
    decomposition: JointParallelDecomposition,
    rho_a: np.ndarray,
    rho_b: np.ndarray,
    observable_a: np.ndarray,
    observable_b: np.ndarray,
) -> complex:
    rho = np.kron(rho_a, rho_b)
    evolved = decomposition.target_unitary @ rho @ decomposition.target_unitary.conj().T
    return np.trace(np.kron(observable_a, observable_b) @ evolved)


def reconstruct_parallel_joint_expectations(
    decomposition: JointParallelDecomposition,
    rho_a: np.ndarray,
    rho_b: np.ndarray,
    observables: Sequence[tuple[np.ndarray, np.ndarray]],
    *,
    available_width_a: int | None = None,
    available_width_b: int | None = None,
) -> JointReconstructionResult:
    """Enumerate all outer QPD terms and signed local branches exactly.

    The outer coefficient is used directly. This exact-enumeration API is
    intentionally distinct from sampling by |a_t|/gamma.
    """
    data_width_a = int(round(np.log2(rho_a.shape[0])))
    data_width_b = int(round(np.log2(rho_b.shape[0])))
    if rho_a.shape != (2**data_width_a, 2**data_width_a) or rho_b.shape != (2**data_width_b, 2**data_width_b):
        raise ValueError("local density matrices must have qubit-power dimensions")
    interference = any(term.term_type == "interference" for term in decomposition.qpd_terms)
    ancillas_a = ancillas_b = 1 if interference else 0
    required_a, required_b = data_width_a + ancillas_a, data_width_b + ancillas_b
    if (available_width_a is not None and required_a > available_width_a) or (
        available_width_b is not None and required_b > available_width_b
    ):
        return JointReconstructionResult(
            0.0, 0.0, decomposition.coefficient_l1_norm, decomposition.sampling_overhead,
            (), float("inf"), required_a, required_b, ancillas_a, ancillas_b, False, "ancilla_capacity"
        )
    generated_gamma = float(sum(abs(term.outer_coefficient_real) for term in decomposition.qpd_terms))
    generated_overhead = generated_gamma * generated_gamma
    errors: list[float] = []
    for observable_a, observable_b in observables:
        reconstructed = sum(
            term.outer_coefficient_real
            * _signed_expectation(term.instrument_a, rho_a, observable_a)
            * _signed_expectation(term.instrument_b, rho_b, observable_b)
            for term in decomposition.qpd_terms
        )
        reference = _target_expectation(decomposition, rho_a, rho_b, observable_a, observable_b)
        errors.append(float(abs(reconstructed - reference)))
    executable = (
        isclose(generated_gamma, decomposition.coefficient_l1_norm, rel_tol=0.0, abs_tol=1e-12)
        and isclose(generated_overhead, decomposition.sampling_overhead, rel_tol=0.0, abs_tol=1e-12)
        and max(errors, default=0.0) < 1e-10
    )
    return JointReconstructionResult(
        generated_gamma, generated_overhead, decomposition.coefficient_l1_norm, decomposition.sampling_overhead,
        tuple(errors), max(errors, default=0.0), required_a, required_b, ancillas_a, ancillas_b,
        executable, None if executable else "reconstruction_or_overhead_mismatch"
    )
