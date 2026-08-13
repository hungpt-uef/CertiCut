"""Phase 10.3 semantic study: executable independent QPD versus Schmidt surrogate."""

from __future__ import annotations

import json
from math import pi
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, CZGate, RZZGate, iSwapGate

from certicut.costs.joint_qpd import JointQPDMode, joint_cost_oracle


ROOT = Path(__file__).resolve().parents[1]


def cases() -> list[tuple[str, QuantumCircuit, tuple[int, ...], tuple[int, ...]]]:
    entries = []
    for name, operations, partition in (
        ("cx_cx_chain_left", ((CXGate(), (0, 1)), (CXGate(), (1, 2))), (0,)),
        ("cx_cx_chain_right", ((CXGate(), (0, 1)), (CXGate(), (1, 2))), (0, 1)),
        ("iswap_iswap_chain", ((iSwapGate(), (0, 1)), (iSwapGate(), (1, 2))), (0,)),
        ("cx_iswap_chain", ((CXGate(), (0, 1)), (iSwapGate(), (1, 2))), (0,)),
        ("rzz_cx_chain", ((RZZGate(pi / 4), (0, 1)), (CXGate(), (1, 2))), (0,)),
        ("cz_rzz_chain", ((CZGate(), (0, 1)), (RZZGate(pi / 4), (1, 2))), (0,)),
        ("parallel_cx", ((CXGate(), (0, 1)), (CXGate(), (2, 3))), (0, 2)),
        ("repeated_cx", ((CXGate(), (0, 1)), (CXGate(), (0, 1))), (0,)),
        ("rzz_zero_cx", ((RZZGate(0), (0, 1)), (CXGate(), (1, 2))), (0,)),
        ("rzz_epsilon", ((RZZGate(0.1), (0, 1)),), (0,)),
        ("cx_cz_parallel", ((CXGate(), (0, 1)), (CZGate(), (0, 1))), (0,)),
    ):
        width = max(max(qubits) for _, qubits in operations) + 1
        circuit = QuantumCircuit(width)
        for operation, qubits in operations:
            circuit.append(operation, qubits)
        entries.append((name, circuit, tuple(range(len(operations))), partition))
    return entries


def main() -> None:
    records = []
    for name, circuit, indices, partition in cases():
        independent = joint_cost_oracle(JointQPDMode.INDEPENDENT_QPD, circuit, indices, partition)
        surrogate = joint_cost_oracle(JointQPDMode.SCHMIDT_SURROGATE, circuit, indices, partition)
        theory = joint_cost_oracle(JointQPDMode.THEORETICAL_JOINT_QPD, circuit, indices, partition)
        record = {
            "case": name,
            "block_qubits": surrogate.metadata["block_qubits"],
            "partition_a": partition,
            "independent_log_overhead": independent.log_overhead,
            "independent_overhead": independent.overhead,
            "schmidt_log_surrogate": surrogate.log_overhead,
            "schmidt_rank": surrogate.metadata["operator_schmidt_rank"],
            "surrogate_minus_independent": surrogate.log_overhead - independent.log_overhead,
            "independent_executable": independent.executable,
            "theory_available": theory.log_overhead is not None,
            "theory_status": theory.theorem_status,
        }
        records.append(record)
        print(
            f"[{name}] independent={record['independent_log_overhead']:.6f}; "
            f"schmidt={record['schmidt_log_surrogate']:.6f}; "
            f"difference={record['surrogate_minus_independent']:.6f}"
        )
    destination = ROOT / "results" / "phase10_3_joint_cost_oracle_study.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
