"""Joint-cut cost semantics with strict separation of executable and surrogate modes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from math import exp, isfinite, log
from typing import Any, Literal, Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from certicut.costs.qpd import QPDCostError, qpd_cost
from certicut.graph.hypergraph import compute_block_schmidt_rank


class JointQPDMode(str, Enum):
    INDEPENDENT_QPD = "independent_qpd"
    SCHMIDT_SURROGATE = "schmidt_surrogate"
    THEORETICAL_JOINT_QPD = "theoretical_joint_qpd"
    SCHMITT_PARALLEL = "joint_qpd_schmitt_parallel"


class JointQPDOracleUnsupported(ValueError):
    """The requested block has no implemented legal joint-QPD construction."""


@dataclass(frozen=True)
class JointQPDApplicability:
    """Legality decision independent from temporal-spatial block discovery."""

    applicable: bool
    theorem_id: str
    partition_a: tuple[int, ...]
    reason: str
    gate_indices: tuple[int, ...]
    parallel_tensor_product_verified: bool


@dataclass(frozen=True)
class JointQPDTheoremCost:
    """Theorem-normalized cost without claiming executable decomposition generation."""

    applicability: JointQPDApplicability
    coefficient_l1_norm: float | None
    sampling_overhead: float | None
    log_sampling_overhead: float | None
    per_gate_kak_abs_coefficients: tuple[tuple[float, ...], ...]
    decomposition_available: bool
    executable: bool
    theorem_reference: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JointCostEstimate:
    """A cost value plus the semantic guarantees required to interpret it safely."""

    mode: JointQPDMode
    block_gate_indices: tuple[int, ...]
    partition_a: tuple[int, ...]
    log_overhead: float | None
    overhead: float | None
    executable: bool
    decomposition_available: bool
    theorem_status: Literal["exact_independent", "surrogate_only", "unimplemented_theory"]
    legality_reason: str
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_block(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if not gate_indices:
        raise ValueError("joint-cost block must contain at least one gate")
    qubits = tuple(sorted({circuit.find_bit(q).index for index in gate_indices for q in circuit.data[index].qubits}))
    if len(qubits) < 2:
        raise ValueError("joint-cost block must span at least two qubits")
    side_a = tuple(sorted(set(partition_a)))
    if not side_a or not set(side_a) < set(qubits):
        raise ValueError("partition_a must be a nonempty proper subset of block qubits")
    return tuple(gate_indices), qubits


def schmitt_parallel_applicability(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> JointQPDApplicability:
    """Check the exact Corollary 4.1 parallel-gate scope, never temporal grouping alone."""
    indices, qubits = _validate_block(circuit, gate_indices, partition_a)
    side_a = set(partition_a)
    minimum, maximum = min(indices), max(indices)
    # Exact mode considers a self-contained parallel gate region only. Any
    # interleaved operation requires a distinct theorem mode and is rejected.
    if any(index not in set(indices) for index in range(minimum, maximum + 1)):
        return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), "parallel tensor-product region contains interleaved instructions", indices, False)
    latest = [0] * circuit.num_qubits
    layers: dict[int, int] = {}
    for index, instruction in enumerate(circuit.data):
        support = [circuit.find_bit(q).index for q in instruction.qubits]
        layer = 1 + max((latest[q] for q in support), default=0)
        for qubit in support:
            latest[qubit] = layer
        if index in indices:
            layers[index] = layer
    if len(set(layers.values())) != 1:
        return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), "parallel tensor-product region requires one common circuit layer", indices, False)
    used_qubits: set[int] = set()
    for index in indices:
        instruction = circuit.data[index]
        support = tuple(circuit.find_bit(q).index for q in instruction.qubits)
        if instruction.operation.num_qubits != 2:
            return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), f"instruction {index} is not two-qubit", indices, False)
        if not (set(support) & side_a and set(support) - side_a):
            return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), f"instruction {index} does not cross the fixed bipartition", indices, False)
        if len(set(support) & side_a) != 1 or len(set(support) - side_a) != 1:
            return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), f"instruction {index} does not have one endpoint on each side", indices, False)
        if used_qubits & set(support):
            return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), "parallel theorem requires pairwise-disjoint two-qubit gate supports", indices, False)
        try:
            matrix = Operator(instruction.operation).data
        except Exception as error:
            return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), f"instruction {index} has no numeric unitary operator: {error}", indices, False)
        if not np.allclose(matrix.conj().T @ matrix, np.eye(4), atol=1e-10):
            return JointQPDApplicability(False, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), f"instruction {index} is not unitary", indices, False)
        used_qubits.update(support)
    return JointQPDApplicability(True, "schmitt2025_corollary_4_1_parallel", tuple(sorted(side_a)), "verified common-layer tensor product of pairwise-disjoint numeric two-qubit unitaries", indices, True)


def _kak_abs_coefficients(operation: Any) -> tuple[float, ...]:
    """Obtain |u_k| from two-qubit operator Schmidt values, invariant under local KAK factors."""
    matrix = Operator(operation).data
    # Qiskit matrix tensor order is (out q1, out q0, in q1, in q0).
    reshuffled = np.transpose(matrix.reshape(2, 2, 2, 2), (1, 3, 0, 2)).reshape(4, 4)
    values = np.linalg.svd(reshuffled, compute_uv=False) / 2.0
    values = tuple(float(value) for value in values if value > 1e-10)
    if not np.isclose(sum(value * value for value in values), 1.0, atol=1e-9):
        raise JointQPDOracleUnsupported("invalid KAK/operator-Schmidt normalization")
    return values


def schmitt_parallel_cost(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> JointQPDTheoremCost:
    """Exact gamma and Gamma for Schmitt--Piveteau--Sutter parallel two-qubit gates.

    Corollary 4.1 gives gamma = 2 prod_i(sum_k |u_{i,k}|)^2 - 1.
    CertiCut's sampling-overhead convention is Gamma = gamma^2 and J = log(Gamma).
    Decomposition generation is intentionally deferred; this function is cost-only.
    """
    applicability = schmitt_parallel_applicability(circuit, gate_indices, partition_a)
    if not applicability.applicable:
        return JointQPDTheoremCost(applicability, None, None, None, (), False, False, "Schmitt, Piveteau, Sutter, Quantum 9, 1634 (2025), Corollary 4.1")
    coefficients = tuple(_kak_abs_coefficients(circuit.data[index].operation) for index in applicability.gate_indices)
    product_l1_squared = float(np.prod([sum(values) ** 2 for values in coefficients]))
    gamma = 2.0 * product_l1_squared - 1.0
    overhead = gamma * gamma
    return JointQPDTheoremCost(
        applicability,
        gamma,
        overhead,
        log(overhead),
        coefficients,
        False,
        False,
        "Schmitt, Piveteau, Sutter, Quantum 9, 1634 (2025), Corollary 4.1",
    )


def independent_qpd_cost(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> JointCostEstimate:
    """Exact executable cost for cutting every crossed two-qubit instruction independently."""
    indices, qubits = _validate_block(circuit, gate_indices, partition_a)
    side_a = set(partition_a)
    log_overhead = 0.0
    crossed: list[int] = []
    for index in indices:
        instruction = circuit.data[index]
        support = tuple(circuit.find_bit(q).index for q in instruction.qubits)
        if instruction.operation.num_qubits != 2:
            raise JointQPDOracleUnsupported(
                f"independent QPD oracle requires two-qubit operations; index {index} is {instruction.operation.name}"
            )
        if not (set(support) & side_a and set(support) - side_a):
            continue
        try:
            log_overhead += qpd_cost(instruction.operation).log_cost
        except QPDCostError as error:
            raise JointQPDOracleUnsupported(str(error)) from error
        crossed.append(index)
    return JointCostEstimate(
        JointQPDMode.INDEPENDENT_QPD,
        indices,
        tuple(sorted(partition_a)),
        log_overhead,
        exp(log_overhead),
        True,
        True,
        "exact_independent",
        "Each crossed two-qubit operation has an executable Qiskit QPDBasis decomposition.",
        {"block_qubits": qubits, "crossed_gate_indices": tuple(crossed)},
    )


def schmidt_surrogate_cost(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> JointCostEstimate:
    """Return log operator-Schmidt rank, explicitly marked as non-executable surrogate."""
    indices, qubits = _validate_block(circuit, gate_indices, partition_a)
    rank = compute_block_schmidt_rank(circuit, indices, qubits, partition_a)
    value = log(float(rank))
    return JointCostEstimate(
        JointQPDMode.SCHMIDT_SURROGATE,
        indices,
        tuple(sorted(partition_a)),
        value,
        float(rank),
        False,
        False,
        "surrogate_only",
        "Operator-Schmidt rank is not asserted to be a QPD overhead or an executable decomposition.",
        {"block_qubits": qubits, "operator_schmidt_rank": rank},
    )


def theoretical_joint_qpd_cost(
    circuit: QuantumCircuit, gate_indices: Sequence[int], partition_a: Sequence[int]
) -> JointCostEstimate:
    """Fail closed until a legal construction from joint-QPD theory is implemented and verified."""
    indices, qubits = _validate_block(circuit, gate_indices, partition_a)
    if any(circuit.data[index].operation.num_qubits != 2 for index in indices):
        reason = "The current oracle boundary admits only blocks composed of two-qubit unitaries."
    else:
        reason = (
            "A closed-form multi-unitary joint-cut theorem exists in the literature, but this repository "
            "does not yet implement its decomposition construction or executable reconstruction semantics."
        )
    return JointCostEstimate(
        JointQPDMode.THEORETICAL_JOINT_QPD,
        indices,
        tuple(sorted(partition_a)),
        None,
        None,
        False,
        False,
        "unimplemented_theory",
        reason,
        {"block_qubits": qubits},
    )


def joint_cost_oracle(
    mode: JointQPDMode | str,
    circuit: QuantumCircuit,
    gate_indices: Sequence[int],
    partition_a: Sequence[int],
) -> JointCostEstimate:
    """Dispatch without silently treating a Schmidt surrogate as legal joint QPD."""
    selected = JointQPDMode(mode)
    if selected is JointQPDMode.INDEPENDENT_QPD:
        return independent_qpd_cost(circuit, gate_indices, partition_a)
    if selected is JointQPDMode.SCHMIDT_SURROGATE:
        return schmidt_surrogate_cost(circuit, gate_indices, partition_a)
    return theoretical_joint_qpd_cost(circuit, gate_indices, partition_a)
