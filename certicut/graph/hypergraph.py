"""Hypergraph circuit blocks and partition-aware operator-Schmidt costs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations, product
from math import log
from typing import Any, Literal, Sequence

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


BlockStrategy = Literal["qubit_pair", "temporal_spatial"]


@dataclass(frozen=True)
class Hyperedge:
    """A gate block represented as one hyperedge over its participating qubits."""

    edge_id: int
    qubits: tuple[int, ...]
    schmidt_rank: int
    weight: float
    gate_indices: tuple[int, ...]
    gate_types: tuple[str, ...]
    pair_gate_counts: tuple[tuple[int, int, int], ...]
    partition_log_ranks: tuple[tuple[tuple[int, ...], float], ...]

    def log_rank_for_partition(self, partition_a: Sequence[int]) -> float:
        """Return log Schmidt rank for an explicit nontrivial block bipartition."""
        key = tuple(sorted(partition_a))
        for candidate, value in self.partition_log_ranks:
            if candidate == key:
                return value
        raise KeyError(f"partition {key} is not present for hyperedge {self.edge_id}")


@dataclass(frozen=True)
class Hypergraph:
    """Hypergraph H=(V,E) and provenance for the selected block strategy."""

    num_qubits: int
    hyperedges: tuple[Hyperedge, ...]
    block_strategy: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _block_subcircuit(
    circuit: QuantumCircuit, gate_indices: Sequence[int], qubits: Sequence[int]
) -> QuantumCircuit:
    qubits_tuple = tuple(sorted(set(qubits)))
    subcircuit = QuantumCircuit(len(qubits_tuple))
    qubit_map = {qubit: index for index, qubit in enumerate(qubits_tuple)}
    for instruction_index in gate_indices:
        instruction = circuit.data[instruction_index]
        local_qubits = [qubit_map[circuit.find_bit(q).index] for q in instruction.qubits]
        subcircuit.append(instruction.operation, local_qubits)
    return subcircuit


def compute_block_schmidt_rank(
    circuit: QuantumCircuit,
    gate_indices: Sequence[int],
    qubits: Sequence[int],
    partition_a: Sequence[int] | None = None,
    *,
    tolerance: float = 1e-7,
) -> int:
    """Compute an operator-Schmidt rank by SVD for a specified block bipartition."""
    qubits_tuple = tuple(sorted(set(qubits)))
    n_block = len(qubits_tuple)
    if n_block <= 1:
        return 1

    subcircuit = _block_subcircuit(circuit, gate_indices, qubits_tuple)
    matrix = Operator(subcircuit).data
    qubit_map = {qubit: index for index, qubit in enumerate(qubits_tuple)}

    if partition_a is None:
        local_a = list(range(n_block // 2))
    else:
        local_a = sorted(qubit_map[q] for q in set(partition_a) if q in qubit_map)
        if not local_a or len(local_a) == n_block:
            raise ValueError("partition_a must be a nonempty proper subset of block qubits")
    local_b = [q for q in range(n_block) if q not in local_a]

    # Qiskit's basis order is q_(n-1)...q_0 for matrix rows and columns.
    tensor = matrix.reshape([2] * (2 * n_block))
    output_a = [n_block - 1 - q for q in local_a]
    input_a = [2 * n_block - 1 - q for q in local_a]
    output_b = [n_block - 1 - q for q in local_b]
    input_b = [2 * n_block - 1 - q for q in local_b]
    reordered = np.transpose(tensor, output_a + input_a + output_b + input_b)
    bipartite = reordered.reshape(2 ** (2 * len(local_a)), 2 ** (2 * len(local_b)))
    singular_values = np.linalg.svd(bipartite, compute_uv=False)
    return max(1, int(np.sum(singular_values > tolerance)))


def _canonical_bipartitions(qubits: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    """Enumerate bipartitions once, retaining only the side containing the first qubit."""
    anchor = qubits[0]
    partitions: list[tuple[int, ...]] = []
    for size in range(1, len(qubits)):
        for subset in combinations(qubits, size):
            if anchor in subset:
                partitions.append(subset)
    return tuple(partitions)


def _instruction_layers(circuit: QuantumCircuit) -> tuple[int, ...]:
    latest = [0] * circuit.num_qubits
    layers: list[int] = []
    for instruction in circuit.data:
        indices = [circuit.find_bit(qubit).index for qubit in instruction.qubits]
        depth = 1 + max((latest[index] for index in indices), default=0)
        for index in indices:
            latest[index] = depth
        layers.append(depth)
    return tuple(layers)


def _pair_blocks(circuit: QuantumCircuit) -> list[list[int]]:
    blocks: dict[tuple[int, ...], list[int]] = {}
    for index, instruction in enumerate(circuit.data):
        if instruction.operation.num_qubits < 2:
            continue
        qubits = tuple(sorted(circuit.find_bit(q).index for q in instruction.qubits))
        blocks.setdefault(qubits, []).append(index)
    return [indices for _, indices in sorted(blocks.items())]


def _temporal_spatial_blocks(
    circuit: QuantumCircuit, *, depth_window: int, max_block_qubits: int
) -> list[list[int]]:
    """Merge temporally nearby interacting gates when their qubit supports overlap."""
    if depth_window < 1:
        raise ValueError("depth_window must be positive")
    if max_block_qubits < 2:
        raise ValueError("max_block_qubits must be at least two")

    layers = _instruction_layers(circuit)
    blocks: list[list[int]] = []
    block_qubits: list[set[int]] = []
    for index, instruction in enumerate(circuit.data):
        if instruction.operation.num_qubits < 2:
            continue
        support = {circuit.find_bit(q).index for q in instruction.qubits}
        placed = False
        for block_index in range(len(blocks) - 1, -1, -1):
            previous = blocks[block_index][-1]
            merged = block_qubits[block_index] | support
            if layers[index] - layers[previous] > depth_window:
                break
            if block_qubits[block_index] & support and len(merged) <= max_block_qubits:
                blocks[block_index].append(index)
                block_qubits[block_index] = merged
                placed = True
                break
        if not placed:
            blocks.append([index])
            block_qubits.append(support)
    return blocks


def _pair_gate_counts(circuit: QuantumCircuit, gate_indices: Sequence[int]) -> tuple[tuple[int, int, int], ...]:
    counts: dict[tuple[int, int], int] = {}
    for index in gate_indices:
        support = tuple(sorted(circuit.find_bit(q).index for q in circuit.data[index].qubits))
        for first, second in combinations(support, 2):
            counts[(first, second)] = counts.get((first, second), 0) + 1
    return tuple((first, second, count) for (first, second), count in sorted(counts.items()))


def build_hypergraph(
    circuit: QuantumCircuit,
    *,
    block_strategy: BlockStrategy = "qubit_pair",
    depth_window: int = 2,
    max_block_qubits: int = 3,
) -> Hypergraph:
    """Build pair or true temporal-spatial joint blocks with exact rank-one weight zero."""
    if block_strategy == "qubit_pair":
        blocks = _pair_blocks(circuit)
    elif block_strategy == "temporal_spatial":
        blocks = _temporal_spatial_blocks(
            circuit, depth_window=depth_window, max_block_qubits=max_block_qubits
        )
    else:
        raise ValueError(f"unknown block strategy '{block_strategy}'")

    hyperedges: list[Hyperedge] = []
    for edge_id, gate_indices in enumerate(blocks):
        qubits = tuple(sorted({circuit.find_bit(q).index for index in gate_indices for q in circuit.data[index].qubits}))
        partitions = _canonical_bipartitions(qubits)
        rank_lookup = tuple(
            (
                partition,
                log(float(compute_block_schmidt_rank(circuit, gate_indices, qubits, partition))),
            )
            for partition in partitions
        )
        default_partition = tuple(qubits[: len(qubits) // 2])
        default_rank = compute_block_schmidt_rank(circuit, gate_indices, qubits, default_partition)
        hyperedges.append(
            Hyperedge(
                edge_id=edge_id,
                qubits=qubits,
                schmidt_rank=default_rank,
                weight=log(float(default_rank)),
                gate_indices=tuple(gate_indices),
                gate_types=tuple(circuit.data[index].operation.name for index in gate_indices),
                pair_gate_counts=_pair_gate_counts(circuit, gate_indices),
                partition_log_ranks=rank_lookup,
            )
        )
    return Hypergraph(circuit.num_qubits, tuple(hyperedges), block_strategy)
