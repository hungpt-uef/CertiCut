"""Executable parallel-joint independently-composed (PJ-QPD) partition objective."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import exp, log
from typing import Sequence

from qiskit import QuantumCircuit

from certicut.costs.joint_qpd import _kak_abs_coefficients


@dataclass(frozen=True)
class ParallelLayerGate:
    instruction_index: int
    layer: int
    qubits: tuple[int, int]
    log_s: float
    independent_log_overhead: float


@dataclass(frozen=True)
class ParallelJointEvaluation:
    independent_log_cost: float
    parallel_joint_log_cost: float
    independent_overhead: float
    parallel_joint_overhead: float
    cut_gate_count: int
    crossed_by_layer: tuple[tuple[int, ...], ...]


def _layers(circuit: QuantumCircuit) -> tuple[int, ...]:
    latest = [0] * circuit.num_qubits
    layers = []
    for instruction in circuit.data:
        support = [circuit.find_bit(q).index for q in instruction.qubits]
        layer = 1 + max((latest[q] for q in support), default=0)
        for qubit in support:
            latest[qubit] = layer
        layers.append(layer)
    return tuple(layers)


def parallel_layer_gates(circuit: QuantumCircuit) -> tuple[ParallelLayerGate, ...]:
    """Extract two-qubit gates and KAK strengths by dependency layer."""
    layers = _layers(circuit)
    gates: list[ParallelLayerGate] = []
    for index, instruction in enumerate(circuit.data):
        if instruction.operation.num_qubits != 2:
            continue
        qubits = tuple(circuit.find_bit(q).index for q in instruction.qubits)
        abs_coefficients = _kak_abs_coefficients(instruction.operation)
        s = sum(abs_coefficients) ** 2
        gates.append(ParallelLayerGate(index, layers[index], qubits, log(s), log((2.0 * s - 1.0) ** 2)))
    return tuple(gates)


def pj_layer_function(total_log_s: float) -> float:
    """f(t)=2 log(2 exp(t)-1), exact for one independently composed legal layer."""
    return 2.0 * log(2.0 * exp(total_log_s) - 1.0)


def evaluate_parallel_joint_partition(circuit: QuantumCircuit, partition: Sequence[int]) -> ParallelJointEvaluation:
    """Evaluate the executable PJ-QPD policy, joint per legal layer and independent across layers."""
    if len(partition) != circuit.num_qubits:
        raise ValueError("partition length must equal circuit.num_qubits")
    by_layer: dict[int, list[ParallelLayerGate]] = {}
    independent = 0.0
    cut_count = 0
    for gate in parallel_layer_gates(circuit):
        if partition[gate.qubits[0]] == partition[gate.qubits[1]]:
            continue
        by_layer.setdefault(gate.layer, []).append(gate)
        independent += gate.independent_log_overhead
        cut_count += 1
    joint = sum(pj_layer_function(sum(gate.log_s for gate in gates)) for gates in by_layer.values())
    return ParallelJointEvaluation(
        independent,
        joint,
        exp(independent),
        exp(joint),
        cut_count,
        tuple(tuple(gate.instruction_index for gate in gates) for _, gates in sorted(by_layer.items())),
    )


def exact_balanced_partitions(num_qubits: int) -> tuple[tuple[int, ...], ...]:
    """Enumerate symmetry-reduced balanced K=2 partitions with qubit zero fixed to side zero."""
    if num_qubits % 2:
        raise ValueError("exact balanced enumeration requires an even qubit count")
    target = num_qubits // 2
    return tuple(
        tuple(0 if qubit in (0, *side_zero_rest) else 1 for qubit in range(num_qubits))
        for side_zero_rest in combinations(range(1, num_qubits), target - 1)
    )
