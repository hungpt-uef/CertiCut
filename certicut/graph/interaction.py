"""Build a deterministic, sampling-aware interaction graph from Qiskit circuits."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import log
from typing import Any, Iterable, Mapping, Sequence

from qiskit import QuantumCircuit

from certicut.costs.qpd import qpd_cost


DEFAULT_QPD_OVERHEADS = {"cx": 9.0}


@dataclass(frozen=True)
class GateOccurrence:
    """Traceable two-qubit instruction retained after edge aggregation."""

    instruction_index: int
    layer_depth: int
    gate_type: str
    control: int | None
    target: int | None
    gate_params: tuple[float, ...] = ()
    qpd_overhead: float = 9.0
    qpd_log_cost: float = log(9.0)
    qpd_source: str = "legacy_cx"


@dataclass(frozen=True)
class InteractionNode:
    qubit: int
    degree: int
    weighted_degree: float
    two_qubit_gate_count: int
    first_active_depth: int | None
    last_active_depth: int | None


@dataclass(frozen=True)
class InteractionEdge:
    u: int
    v: int
    gate_count: int
    gate_type_counts: dict[str, int]
    instruction_indices: tuple[int, ...]
    depths: tuple[int, ...]
    first_depth: int
    last_depth: int
    qpd_log_cost: float
    gates: tuple[GateOccurrence, ...]


@dataclass(frozen=True)
class InteractionGraph:
    num_qubits: int
    nodes: tuple[InteractionNode, ...]
    edges: tuple[InteractionEdge, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_interaction_graph(
    circuit: QuantumCircuit,
    *,
    qpd_overheads: Mapping[str, float] | None = None,
    cost_model: str = "legacy_cx",
) -> InteractionGraph:
    """Aggregate supported two-qubit gates into deterministic undirected edges."""
    overheads = dict(DEFAULT_QPD_OVERHEADS if qpd_overheads is None else qpd_overheads)
    if any(value <= 0 for value in overheads.values()):
        raise ValueError("QPD overheads must be positive")

    active_depths: list[list[int]] = [[] for _ in range(circuit.num_qubits)]
    latest_layer = [0] * circuit.num_qubits
    occurrences: dict[tuple[int, int], list[GateOccurrence]] = {}

    for instruction_index, instruction in enumerate(circuit.data):
        qubits = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        layer_depth = 1 + max((latest_layer[qubit] for qubit in qubits), default=0)
        for qubit in qubits:
            latest_layer[qubit] = layer_depth
            active_depths[qubit].append(layer_depth)

        if instruction.operation.num_qubits != 2:
            continue
        gate_type = instruction.operation.name
        if cost_model == "qiskit_qpd":
            cost = qpd_cost(instruction.operation)
        elif cost_model == "legacy_cx":
            if gate_type not in overheads:
                raise ValueError(f"No QPD overhead configured for two-qubit gate '{gate_type}'")
            cost = None
        else:
            raise ValueError(f"unknown cost model '{cost_model}'")
        control, target = qubits
        edge_key = tuple(sorted((control, target)))
        occurrences.setdefault(edge_key, []).append(
            GateOccurrence(
                instruction_index, layer_depth, gate_type, control, target,
                cost.gate_params if cost else (), cost.overhead if cost else overheads[gate_type],
                cost.log_cost if cost else log(overheads[gate_type]), cost.source if cost else "legacy_cx",
            )
        )

    edges = tuple(
        _build_edge(u, v, edge_gates)
        for (u, v), edge_gates in sorted(occurrences.items())
    )
    nodes = _build_nodes(circuit.num_qubits, edges, active_depths)
    return InteractionGraph(circuit.num_qubits, nodes, edges)


def graph_partition_objective(graph: InteractionGraph, partition: Sequence[int]) -> float:
    """Return sum of crossed aggregate edge costs for a qubit partition."""
    if len(partition) != graph.num_qubits:
        raise ValueError("partition length must equal graph.num_qubits")
    return sum(edge.qpd_log_cost for edge in graph.edges if partition[edge.u] != partition[edge.v])


def fixed_capacity_cross_pair_count(fragment_sizes: Sequence[int]) -> int:
    """Return the complete-graph cross-pair count for exact fragment sizes.

    For K=2 balanced fragments this is ``n**2 // 4``. It is useful for
    K-way polyhedral analysis only when every fragment size is fixed exactly.
    """
    if any(size < 0 for size in fragment_sizes):
        raise ValueError("fragment sizes must be nonnegative")
    total = sum(fragment_sizes)
    return total * (total - 1) // 2 - sum(size * (size - 1) // 2 for size in fragment_sizes)


def gate_level_partition_objective(
    circuit: QuantumCircuit,
    partition: Sequence[int],
    *,
    qpd_overheads: Mapping[str, float] | None = None,
    cost_model: str = "legacy_cx",
) -> float:
    """Reference objective evaluated directly from circuit instructions."""
    if len(partition) != circuit.num_qubits:
        raise ValueError("partition length must equal circuit.num_qubits")
    overheads = DEFAULT_QPD_OVERHEADS if qpd_overheads is None else qpd_overheads
    cost = 0.0
    for instruction in circuit.data:
        if instruction.operation.num_qubits != 2:
            continue
        gate_type = instruction.operation.name
        if cost_model == "qiskit_qpd":
            gate_cost = qpd_cost(instruction.operation).log_cost
        elif cost_model == "legacy_cx":
            if gate_type not in overheads:
                raise ValueError(f"No QPD overhead configured for two-qubit gate '{gate_type}'")
            gate_cost = log(overheads[gate_type])
        else:
            raise ValueError(f"unknown cost model '{cost_model}'")
        control, target = (circuit.find_bit(qubit).index for qubit in instruction.qubits)
        if partition[control] != partition[target]:
            cost += gate_cost
    return cost


def valid_two_fragment_partitions(num_qubits: int, qmax: int) -> Iterable[tuple[int, ...]]:
    """Yield symmetry-reduced feasible two-fragment labels with q0 fixed in fragment zero."""
    if num_qubits < 2 or num_qubits > 2 * qmax:
        return
    for mask in range(1 << (num_qubits - 1)):
        partition = (0, *(1 if mask & (1 << index) else 0 for index in range(num_qubits - 1)))
        first_size = partition.count(0)
        second_size = num_qubits - first_size
        if first_size <= qmax and second_size <= qmax:
            yield partition


def _build_edge(
    u: int,
    v: int,
    gates: list[GateOccurrence],
) -> InteractionEdge:
    gate_type_counts: dict[str, int] = {}
    for gate in gates:
        gate_type_counts[gate.gate_type] = gate_type_counts.get(gate.gate_type, 0) + 1
    depths = tuple(gate.layer_depth for gate in gates)
    return InteractionEdge(
        u=u,
        v=v,
        gate_count=len(gates),
        gate_type_counts=dict(sorted(gate_type_counts.items())),
        instruction_indices=tuple(gate.instruction_index for gate in gates),
        depths=depths,
        first_depth=min(depths),
        last_depth=max(depths),
        qpd_log_cost=sum(gate.qpd_log_cost for gate in gates),
        gates=tuple(gates),
    )


def _build_nodes(
    num_qubits: int,
    edges: Sequence[InteractionEdge],
    active_depths: Sequence[Sequence[int]],
) -> tuple[InteractionNode, ...]:
    neighbours = [set() for _ in range(num_qubits)]
    weighted_degrees = [0.0] * num_qubits
    gate_counts = [0] * num_qubits
    for edge in edges:
        neighbours[edge.u].add(edge.v)
        neighbours[edge.v].add(edge.u)
        weighted_degrees[edge.u] += edge.qpd_log_cost
        weighted_degrees[edge.v] += edge.qpd_log_cost
        gate_counts[edge.u] += edge.gate_count
        gate_counts[edge.v] += edge.gate_count
    return tuple(
        InteractionNode(
            qubit=qubit,
            degree=len(neighbours[qubit]),
            weighted_degree=weighted_degrees[qubit],
            two_qubit_gate_count=gate_counts[qubit],
            first_active_depth=min(active_depths[qubit]) if active_depths[qubit] else None,
            last_active_depth=max(active_depths[qubit]) if active_depths[qubit] else None,
        )
        for qubit in range(num_qubits)
    )
