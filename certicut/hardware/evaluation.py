"""Offline fragment transpilation and controlled Aer noise diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log
from typing import Any, Sequence

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Pauli, Statevector
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit_aer import AerSimulator


@dataclass(frozen=True)
class FragmentHardwareMetrics:
    fragment: int
    logical_qubits: tuple[int, ...]
    mapped_two_qubit_gates: int
    routing_added_two_qubit_gates: int
    mapped_depth: int


@dataclass(frozen=True)
class HardwareEvaluation:
    topology: str
    fragments: tuple[FragmentHardwareMetrics, ...]
    total_two_qubit_gates: int
    total_routing_added_two_qubit_gates: int
    maximum_depth: int
    negative_log_success_surrogate: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoisyObservableEvaluation:
    shots: int
    exact_z_expectation: float
    noisy_z_expectation: float
    absolute_error: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_fragments(
    circuit: QuantumCircuit,
    partition: Sequence[int],
    *,
    topology: str = "grid",
    two_qubit_error: float = 0.01,
) -> HardwareEvaluation:
    """Map local retained gates; cut gates are intentionally excluded.

    This is a routing diagnostic, not exact global hardware mapping or a noisy
    circuit-cutting reconstruction estimate.
    """
    if len(partition) != circuit.num_qubits:
        raise ValueError("partition length must equal circuit width")
    if not 0 <= two_qubit_error < 1:
        raise ValueError("two_qubit_error must lie in [0, 1)")
    labels = tuple(sorted(set(partition)))
    metrics = tuple(
        _evaluate_fragment(circuit, tuple(qubit for qubit, label in enumerate(partition) if label == fragment), fragment, topology)
        for fragment in labels
    )
    total_two_qubit = sum(metric.mapped_two_qubit_gates for metric in metrics)
    routing_added = sum(metric.routing_added_two_qubit_gates for metric in metrics)
    return HardwareEvaluation(
        topology, metrics, total_two_qubit, routing_added, max((metric.mapped_depth for metric in metrics), default=0),
        total_two_qubit * -log(1.0 - two_qubit_error),
    )


def controlled_noise_model(*, one_qubit_error: float = 1e-4, two_qubit_error: float = 1e-2, readout_error: float = 2e-2) -> NoiseModel:
    """Build a declared synthetic depolarizing/readout model for Aer studies."""
    if not all(0 <= value < 1 for value in (one_qubit_error, two_qubit_error, readout_error)):
        raise ValueError("noise rates must lie in [0, 1)")
    model = NoiseModel()
    model.add_all_qubit_quantum_error(depolarizing_error(one_qubit_error, 1), ["id", "rz", "sx", "x"])
    model.add_all_qubit_quantum_error(depolarizing_error(two_qubit_error, 2), ["cx", "ecr"])
    model.add_all_qubit_readout_error(
        ReadoutError([[1.0 - readout_error, readout_error], [readout_error, 1.0 - readout_error]])
    )
    return model


def evaluate_noisy_z_observable(circuit: QuantumCircuit, noise_model: NoiseModel, *, shots: int = 4096, seed: int = 0) -> NoisyObservableEvaluation:
    """Estimate the all-Z expectation under a declared Aer noise model."""
    if shots < 1:
        raise ValueError("shots must be positive")
    exact = float(Statevector(circuit).expectation_value(Pauli("Z" * circuit.num_qubits)).real)
    measured = circuit.copy()
    measured.measure_all()
    result = AerSimulator(noise_model=noise_model, seed_simulator=seed).run(measured, shots=shots).result()
    counts = result.get_counts()
    expectation = sum((1 if bitstring.count("1") % 2 == 0 else -1) * count for bitstring, count in counts.items()) / shots
    return NoisyObservableEvaluation(shots, exact, expectation, abs(exact - expectation))


def _evaluate_fragment(circuit: QuantumCircuit, qubits: tuple[int, ...], fragment: int, topology: str) -> FragmentHardwareMetrics:
    if not qubits:
        return FragmentHardwareMetrics(fragment, qubits, 0, 0, 0)
    mapping = {qubit: local for local, qubit in enumerate(qubits)}
    local = QuantumCircuit(len(qubits))
    for instruction in circuit.data:
        support = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        if not set(support) <= set(qubits):
            continue
        local.append(instruction.operation, [mapping[qubit] for qubit in support])
    backend = _backend(len(qubits), topology)
    mapped = transpile(local, backend=backend, optimization_level=1, seed_transpiler=0)
    counts = mapped.count_ops()
    two_qubit = sum(count for gate, count in counts.items() if gate in {"cx", "ecr", "cz", "iswap", "swap"})
    original_two_qubit = sum(instruction.operation.num_qubits == 2 for instruction in local.data)
    return FragmentHardwareMetrics(fragment, qubits, int(two_qubit), max(0, int(two_qubit) - original_two_qubit), mapped.depth())


def _backend(num_qubits: int, topology: str) -> GenericBackendV2:
    if topology == "all_to_all":
        coupling = CouplingMap.from_full(num_qubits)
    elif topology == "line":
        coupling = CouplingMap.from_line(num_qubits)
    elif topology == "grid":
        rows = max(1, int(num_qubits**0.5))
        columns = (num_qubits + rows - 1) // rows
        edges = []
        for qubit in range(num_qubits):
            row, column = divmod(qubit, columns)
            for neighbor in (qubit + 1 if column + 1 < columns else None, qubit + columns if row + 1 < rows else None):
                if neighbor is not None and neighbor < num_qubits:
                    edges.extend(((qubit, neighbor), (neighbor, qubit)))
        coupling = CouplingMap(edges)
    else:
        raise ValueError("topology must be all_to_all, line, or grid")
    return GenericBackendV2(num_qubits=num_qubits, basis_gates=["id", "rz", "sx", "x", "cx"], coupling_map=coupling)
