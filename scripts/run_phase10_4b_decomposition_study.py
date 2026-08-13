"""Phase 10.4B theorem-backed parallel joint-QPD algebraic decomposition study."""

from __future__ import annotations

import json
from math import pi
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, CZGate, RZZGate, iSwapGate

from certicut.costs.joint_parallel import build_schmitt_parallel_decomposition
from certicut.costs.joint_qpd import schmitt_parallel_applicability


ROOT = Path(__file__).resolve().parents[1]


def _parallel_case(name, operations):
    width = max(max(qubits) for _, qubits in operations) + 1
    circuit = QuantumCircuit(width)
    for operation, qubits in operations:
        circuit.append(operation, qubits)
    indices = tuple(range(len(operations)))
    partition = tuple(sorted(qubits[0] for _, qubits in operations))
    return name, circuit, indices, partition


def _illegal_temporal_case():
    circuit = QuantumCircuit(3)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    return "illegal_temporal_overlap", circuit, (0, 1), (0, 2)


def cases():
    return (
        _parallel_case("single_cx", ((CXGate(), (0, 1)),)),
        _parallel_case("single_cz", ((CZGate(), (0, 1)),)),
        _parallel_case("single_rzz", ((RZZGate(pi / 4), (0, 1)),)),
        _parallel_case("single_iswap", ((iSwapGate(), (0, 1)),)),
        _parallel_case("parallel_cx_2", ((CXGate(), (0, 2)), (CXGate(), (1, 3)))),
        _parallel_case("parallel_cx_3", ((CXGate(), (0, 3)), (CXGate(), (1, 4)), (CXGate(), (2, 5)))),
        _parallel_case("parallel_iswap_2", ((iSwapGate(), (0, 2)), (iSwapGate(), (1, 3)))),
        _parallel_case("parallel_mixed_cx_rzz", ((CXGate(), (0, 2)), (RZZGate(pi / 4), (1, 3)))),
        _parallel_case("parallel_weak_rzz", ((RZZGate(0.1), (0, 2)), (RZZGate(0.1), (1, 3)))),
        _illegal_temporal_case(),
    )


def main() -> None:
    records = []
    for name, circuit, indices, partition in cases():
        eligibility = schmitt_parallel_applicability(circuit, indices, partition)
        record = {
            "block_id": name,
            "partition_a": partition,
            "theorem_applicable": eligibility.applicable,
            "parallel_tensor_product_verified": eligibility.parallel_tensor_product_verified,
            "reason": eligibility.reason,
        }
        if eligibility.applicable:
            decomposition = build_schmitt_parallel_decomposition(circuit, indices, partition)
            record.update({
                "composite_term_count": len(decomposition.composite_kak_terms),
                "outer_qpd_term_count": len(decomposition.qpd_terms),
                "coefficient_l1_norm_gamma": decomposition.coefficient_l1_norm,
                "sampling_overhead_gamma_squared": decomposition.sampling_overhead,
                "log_sampling_overhead": decomposition.log_sampling_overhead,
                "composite_kak_reconstruction_error": decomposition.composite_kak_reconstruction_error,
                "algebraic_reconstruction_error": decomposition.algebraic_reconstruction_error,
                "algebraically_verified": decomposition.algebraically_verified,
                "interference_ancilla_requirement": 1 if any(t.term_type == "interference" for t in decomposition.qpd_terms) else 0,
                "operationally_executable": decomposition.operationally_executable,
            })
        records.append(record)
        print(f"[{name}] applicable={eligibility.applicable}; terms={record.get('outer_qpd_term_count')}; error={record.get('algebraic_reconstruction_error')}")
    destination = ROOT / "results" / "phase10_4b_parallel_decomposition_study.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
