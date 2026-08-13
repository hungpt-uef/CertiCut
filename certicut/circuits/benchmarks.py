"""Deterministic optimizer-only CNOT benchmark circuit families."""

from __future__ import annotations

import random
from math import pi

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, iSwapGate


def make_benchmark_circuit(family: str, num_qubits: int, seed: int) -> QuantumCircuit:
    """Create a deterministic CNOT-only interaction topology without simulation."""
    if num_qubits < 2:
        raise ValueError("num_qubits must be at least two")
    circuit = QuantumCircuit(num_qubits)
    generator = random.Random(seed)
    if family == "random":
        for _ in range(2 * num_qubits):
            circuit.cx(*generator.sample(range(num_qubits), 2))
    elif family == "nearest_neighbor":
        for layer in range(3):
            for qubit in range(layer % 2, num_qubits - 1, 2):
                circuit.cx(qubit, qubit + 1)
    elif family == "qaoa_ring":
        for _ in range(2):
            for qubit in range(num_qubits):
                circuit.cx(qubit, (qubit + 1) % num_qubits)
    elif family == "dense":
        pairs = [(u, v) for u in range(num_qubits) for v in range(u + 1, num_qubits)]
        generator.shuffle(pairs)
        for control, target in pairs[: min(len(pairs), 3 * num_qubits)]:
            circuit.cx(control, target)
    elif family == "community":
        split = num_qubits // 2
        for group in (range(split), range(split, num_qubits)):
            members = list(group)
            for _ in range(2 * len(members)):
                circuit.cx(*generator.sample(members, 2))
        circuit.cx(split - 1, split)
        circuit.cx(split - 2, split + 1)
    elif family == "noisy_community":
        split = num_qubits // 2
        for u in range(num_qubits):
            for v in range(u + 1, num_qubits):
                same_group = (u < split) == (v < split)
                if generator.random() < (0.45 if same_group else 0.18):
                    circuit.cx(u, v)
    elif family == "weighted_random":
        for u in range(num_qubits):
            for v in range(u + 1, num_qubits):
                if generator.random() < 0.22:
                    for _ in range(generator.randint(1, 5)):
                        circuit.cx(u, v)
    else:
        raise ValueError(f"unsupported benchmark family '{family}'")
    return circuit


def make_heterogeneous_qpd_circuit(family: str, num_qubits: int, seed: int) -> QuantumCircuit:
    """Create a deterministic balanced-bisection corpus with Qiskit-QPD gate costs."""
    if num_qubits < 4 or num_qubits % 2:
        raise ValueError("heterogeneous QPD circuits require an even size of at least four")
    generator = random.Random(seed)
    pairs = _heterogeneous_pairs(family, num_qubits, generator)
    circuit = QuantumCircuit(num_qubits)
    palette = ("cx", "cz", "iswap", "rzz_pi8", "rzz_pi4", "rzz_pi2")
    for index, (u, v) in enumerate(pairs):
        operation = palette[index % len(palette)]
        if operation == "cx":
            circuit.cx(u, v)
        elif operation == "cz":
            circuit.cz(u, v)
        elif operation == "iswap":
            circuit.append(iSwapGate(), [u, v])
        elif operation == "rzz_pi8":
            circuit.append(RZZGate(pi / 8), [u, v])
        elif operation == "rzz_pi4":
            circuit.append(RZZGate(pi / 4), [u, v])
        else:
            circuit.append(RZZGate(pi / 2), [u, v])
    return circuit


def _heterogeneous_pairs(family: str, num_qubits: int, generator: random.Random) -> list[tuple[int, int]]:
    """Return at least three deterministic interaction layers for each topology."""
    def matching(nodes: list[int]) -> list[tuple[int, int]]:
        generator.shuffle(nodes)
        return [(nodes[index], nodes[index + 1]) for index in range(0, len(nodes) - 1, 2)]

    if family == "random_matching":
        return [pair for _ in range(4) for pair in matching(list(range(num_qubits)))]
    if family == "ring_even_odd":
        pairs = []
        for layer in range(4):
            pairs.extend((qubit, (qubit + 1) % num_qubits) for qubit in range(layer % 2, num_qubits, 2))
        return pairs
    if family == "community_matching":
        split = num_qubits // 2
        pairs = []
        for _ in range(3):
            pairs.extend(matching(list(range(split))))
            pairs.extend(matching(list(range(split, num_qubits))))
            pairs.extend(((split - 1, split), (split - 2, split + 1)))
        return pairs
    if family == "dense_shuffled":
        pairs = [(u, v) for u in range(num_qubits) for v in range(u + 1, num_qubits)]
        generator.shuffle(pairs)
        return pairs[: 3 * num_qubits]
    if family == "weighted_repeat":
        backbone = [(qubit, (qubit + 1) % num_qubits) for qubit in range(num_qubits)]
        chords = [(qubit, (qubit + num_qubits // 2) % num_qubits) for qubit in range(num_qubits // 2)]
        pairs = []
        for pair in backbone + chords:
            pairs.extend([pair] * generator.randint(1, 4))
        return pairs
    raise ValueError(f"unsupported heterogeneous QPD family '{family}'")
