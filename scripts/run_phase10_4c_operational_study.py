"""Phase 10.4C exact operational reconstruction study for legal parallel joint QPD."""

from __future__ import annotations

import json
from math import pi
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, RYGate, RZGate, RZZGate, UnitaryGate, iSwapGate

from certicut.costs.joint_parallel import build_schmitt_parallel_decomposition
from certicut.costs.joint_qpd import schmitt_parallel_applicability
from certicut.qiskit_bridge.joint_parallel import reconstruct_parallel_joint_expectations


ROOT = Path(__file__).resolve().parents[1]
I = np.eye(2, dtype=complex)
X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
Y = np.array([[0.0, -1j], [1j, 0.0]], dtype=complex)
Z = np.diag([1.0, -1.0])


def _state(vector: np.ndarray) -> np.ndarray:
    return np.outer(vector, vector.conj())


def _inputs(width: int) -> tuple[np.ndarray, np.ndarray]:
    zero = np.array([1.0, 0.0], dtype=complex)
    plus = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2.0)
    minus_y = np.array([1.0, -1j], dtype=complex) / np.sqrt(2.0)
    a = np.array([[1.0 + 0.0j]])
    b = np.array([[1.0 + 0.0j]])
    seeds = ((plus, zero), (minus_y, plus), (zero, minus_y))
    for index in range(width):
        left, right = seeds[index % len(seeds)]
        a = np.kron(a, left)
        b = np.kron(b, right)
    return _state(a), _state(b)


def _observables(width: int):
    patterns = ((Z, X), (X, Y), (Y, Z), (X, X), (Z, Z), (Y, X))
    result = []
    for left_seed, right_seed in patterns:
        left = np.array([[1.0 + 0.0j]])
        right = np.array([[1.0 + 0.0j]])
        for index in range(width):
            left = np.kron(left, left_seed if index == 0 else (Z if index % 2 else I))
            right = np.kron(right, right_seed if index == 0 else (X if index % 2 else I))
        result.append((left, right))
    # Deterministic Pauli sum, represented as one observable pair per product term.
    return tuple(result)


def _case(name, operations):
    width = max(max(qubits) for _, qubits in operations) + 1
    circuit = QuantumCircuit(width)
    for operation, qubits in operations:
        circuit.append(operation, qubits)
    return name, circuit, tuple(range(len(operations))), tuple(qubits[0] for _, qubits in operations)


def _dressed_cx():
    # Local dressing is absorbed by the full KAK pre/post factors.
    # Use a direct numeric two-qubit unitary to preserve a single gate occurrence.
    pre = np.kron(RYGate(0.37).to_matrix(), RZGate(-0.21).to_matrix())
    post = np.kron(RZGate(0.29).to_matrix(), RYGate(0.41).to_matrix())
    return _case("locally_dressed_cx", ((UnitaryGate(post @ CXGate().to_matrix() @ pre), (0, 1)),))


def cases():
    return (
        _case("single_cx", ((CXGate(), (0, 1)),)),
        _case("single_rzz_pi4", ((RZZGate(pi / 4), (0, 1)),)),
        _case("single_iswap", ((iSwapGate(), (0, 1)),)),
        _case("parallel_cx_2", ((CXGate(), (0, 2)), (CXGate(), (1, 3)))),
        _case("parallel_cx_rzz", ((CXGate(), (0, 2)), (RZZGate(pi / 4), (1, 3)))),
        _case("parallel_iswap_2", ((iSwapGate(), (0, 2)), (iSwapGate(), (1, 3)))),
        _case("parallel_weak_rzz", ((RZZGate(0.1), (0, 2)), (RZZGate(0.1), (1, 3)))),
        _dressed_cx(),
    )


def main() -> None:
    records = []
    for name, circuit, indices, partition in cases():
        eligibility = schmitt_parallel_applicability(circuit, indices, partition)
        if not eligibility.applicable:
            raise RuntimeError(f"micro-corpus case unexpectedly ineligible: {name}: {eligibility.reason}")
        decomposition = build_schmitt_parallel_decomposition(circuit, indices, partition)
        width = len(indices)
        result = reconstruct_parallel_joint_expectations(
            decomposition, *_inputs(width), _observables(width)
        )
        record = {
            "block_id": name,
            "theorem_applicable": eligibility.applicable,
            "parallel_tensor_product_verified": eligibility.parallel_tensor_product_verified,
            "observables": 6,
            "gamma_theorem": result.theorem_gamma,
            "gamma_generated": result.generated_gamma,
            "overhead_theorem": result.theorem_overhead,
            "overhead_generated": result.generated_overhead,
            "max_observable_error": result.max_observable_error,
            "required_fragment_width_a": result.required_width_a,
            "required_fragment_width_b": result.required_width_b,
            "ancilla_qubits_a": result.ancilla_qubits_a,
            "ancilla_qubits_b": result.ancilla_qubits_b,
            "outer_qpd_terms": len(decomposition.qpd_terms),
            "operationally_executable": result.operationally_executable,
            "reason": result.reason,
        }
        records.append(record)
        print(f"[{name}] gamma={result.generated_gamma:.12g}; Gamma={result.generated_overhead:.12g}; max_error={result.max_observable_error:.3e}")
    destination = ROOT / "results" / "phase10_4c_operational_joint_reconstruction.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
