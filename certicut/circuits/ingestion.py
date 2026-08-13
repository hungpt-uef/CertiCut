"""Audited logical CNOT ingestion for real MQT Bench circuits."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import pi
from typing import Any

from qiskit import QuantumCircuit, transpile

from certicut.costs.qpd import QPDCostError, qpd_cost

V1_BASIS_GATES = ("rz", "sx", "x", "cx")


@dataclass(frozen=True)
class CircuitAudit:
    source: str
    representation: str
    source_fingerprint: str
    cost_model: str
    parameter_binding: str
    family: str
    num_qubits: int
    transpile_basis: tuple[str, ...]
    optimization_level: int
    seed_transpiler: int
    original_depth: int
    original_ops: dict[str, int]
    original_two_qubit_count: int
    transpiled_two_qubit_count: int
    transpiled_depth: int
    transpiled_ops: dict[str, int]
    cx_count: int
    two_qubit_gate_types: tuple[str, ...]
    unsupported_two_qubit_gates: tuple[str, ...]
    circuit_fingerprint: str
    audit_passed: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def ingest_mqt_benchmark(
    family: str, num_qubits: int, *, seed_transpiler: int = 0,
    representation: str = "cx_normalized",
) -> tuple[QuantumCircuit, CircuitAudit]:
    """Generate one MQT source circuit as an audited CX-normalized or native-QPD representation."""
    from mqt.bench import get_benchmark_alg

    original = get_benchmark_alg(family, circuit_size=num_qubits, random_parameters=False)
    logical = _bind_parameters(_without_measurements(original))
    if representation == "cx_normalized":
        transpiled = transpile(
            logical, basis_gates=list(V1_BASIS_GATES), coupling_map=None,
            optimization_level=1, seed_transpiler=seed_transpiler,
        )
        cost_model = "qiskit_qpd_0.10_independent"
    elif representation == "native_qpd":
        transpiled = _decompose_to_two_qubits(logical)
        cost_model = "qiskit_qpd_0.10_independent"
    else:
        raise ValueError(f"unknown representation '{representation}'")
    two_qubit_types = tuple(sorted({instruction.operation.name for instruction in transpiled.data if instruction.operation.num_qubits == 2}))
    unsupported = []
    for instruction in transpiled.data:
        if instruction.operation.num_qubits > 2:
            unsupported.append(f"arity_{instruction.operation.num_qubits}:{instruction.operation.name}")
        elif instruction.operation.num_qubits == 2:
            try:
                qpd_cost(instruction.operation)
            except QPDCostError as error:
                unsupported.append(f"{instruction.operation.name}:{error}")
    audit = CircuitAudit(
        source="MQTBench==2.2.2", representation=representation, source_fingerprint=_fingerprint(logical), cost_model=cost_model,
        parameter_binding="all_source_parameters=pi/4",
        family=family, num_qubits=num_qubits,
        transpile_basis=V1_BASIS_GATES, optimization_level=1, seed_transpiler=seed_transpiler,
        original_depth=logical.depth(), original_ops=_op_counts(logical), original_two_qubit_count=_two_qubit_count(logical),
        transpiled_depth=transpiled.depth(), transpiled_ops=_op_counts(transpiled), transpiled_two_qubit_count=_two_qubit_count(transpiled),
        cx_count=sum(1 for instruction in transpiled.data if instruction.operation.name == "cx"),
        two_qubit_gate_types=two_qubit_types, unsupported_two_qubit_gates=tuple(unsupported),
        circuit_fingerprint=_fingerprint(transpiled), audit_passed=not unsupported,
    )
    if not audit.audit_passed:
        raise ValueError(f"V1 audit failed: unsupported two-qubit gates {unsupported}")
    return transpiled, audit


def ingest_mqt_pair(family: str, num_qubits: int, *, seed_transpiler: int = 0) -> dict[str, tuple[QuantumCircuit, CircuitAudit]]:
    """Create paired representations from one deterministic MQT source circuit specification."""
    cx = ingest_mqt_benchmark(family, num_qubits, seed_transpiler=seed_transpiler, representation="cx_normalized")
    native = ingest_mqt_benchmark(family, num_qubits, seed_transpiler=seed_transpiler, representation="native_qpd")
    if cx[1].source_fingerprint != native[1].source_fingerprint:
        raise RuntimeError("paired representations were not derived from the same source circuit")
    return {"cx_normalized": cx, "native_qpd": native}


def _without_measurements(circuit: QuantumCircuit) -> QuantumCircuit:
    output = QuantumCircuit(circuit.num_qubits)
    for instruction in circuit.data:
        if instruction.operation.name in {"measure", "barrier"}:
            continue
        output.append(
            instruction.operation,
            [output.qubits[circuit.find_bit(qubit).index] for qubit in instruction.qubits],
            (),
        )
    return output


def _bind_parameters(circuit: QuantumCircuit) -> QuantumCircuit:
    """Use one fixed numeric source instance for both paired representations."""
    if not circuit.parameters:
        return circuit
    return circuit.assign_parameters({parameter: pi / 4 for parameter in circuit.parameters}, inplace=False)


def _decompose_to_two_qubits(circuit: QuantumCircuit) -> QuantumCircuit:
    """Recursively decompose only >2q instructions; preserve supported native 2q operations."""
    output = QuantumCircuit(circuit.num_qubits)

    def append(operation, indices: list[int]) -> None:
        if operation.num_qubits <= 2:
            output.append(operation, [output.qubits[index] for index in indices], ())
            return
        definition = operation.definition
        if definition is None:
            raise ValueError(f"cannot decompose {operation.num_qubits}-qubit operation '{operation.name}'")
        for instruction in definition.data:
            child_indices = [indices[definition.find_bit(qubit).index] for qubit in instruction.qubits]
            append(instruction.operation, child_indices)

    for instruction in circuit.data:
        append(instruction.operation, [circuit.find_bit(qubit).index for qubit in instruction.qubits])
    return output


def _op_counts(circuit: QuantumCircuit) -> dict[str, int]:
    return dict(sorted(Counter(instruction.operation.name for instruction in circuit.data).items()))


def _two_qubit_count(circuit: QuantumCircuit) -> int:
    return sum(instruction.operation.num_qubits == 2 for instruction in circuit.data)


def _fingerprint(circuit: QuantumCircuit) -> str:
    payload = "\n".join(
        f"{instruction.operation.name}:{','.join(str(circuit.find_bit(qubit).index) for qubit in instruction.qubits)}"
        for instruction in circuit.data
    )
    return sha256(payload.encode("utf-8")).hexdigest()
