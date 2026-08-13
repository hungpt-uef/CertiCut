from math import isclose, log

from qiskit import QuantumCircuit

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import (
    build_interaction_graph,
    gate_level_partition_objective,
    graph_partition_objective,
    valid_two_fragment_partitions,
)


def test_phase0_toy_graph_has_expected_topology_and_metadata() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    assert graph.num_qubits == 6
    assert len(graph.nodes) == 6
    assert [(edge.u, edge.v) for edge in graph.edges] == [
        (0, 1), (1, 2), (1, 4), (2, 3), (3, 4), (4, 5)
    ]
    assert all(edge.gate_count == 1 for edge in graph.edges)
    assert all(edge.gate_type_counts == {"cx": 1} for edge in graph.edges)
    assert all(isclose(edge.qpd_log_cost, log(9), abs_tol=1e-12) for edge in graph.edges)
    cross_edge = next(edge for edge in graph.edges if (edge.u, edge.v) == (1, 4))
    assert cross_edge.instruction_indices == (4,)
    assert cross_edge.gates[0].control == 1
    assert cross_edge.gates[0].target == 4


def test_multiple_and_reverse_cnot_gates_aggregate_on_one_undirected_edge() -> None:
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    circuit.cx(1, 0)
    circuit.cx(0, 1)
    graph = build_interaction_graph(circuit)
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert (edge.u, edge.v) == (0, 1)
    assert edge.gate_count == 3
    assert edge.instruction_indices == (0, 1, 2)
    assert [(gate.control, gate.target) for gate in edge.gates] == [(0, 1), (1, 0), (0, 1)]
    assert isclose(edge.qpd_log_cost, 3 * log(9), abs_tol=1e-12)


def test_single_qubit_gates_do_not_create_edges_and_isolated_qubits_remain_nodes() -> None:
    circuit = QuantumCircuit(4)
    circuit.h(0)
    circuit.x(1)
    circuit.rz(0.25, 2)
    circuit.cx(0, 1)
    graph = build_interaction_graph(circuit)
    assert graph.num_qubits == 4
    assert [(edge.u, edge.v) for edge in graph.edges] == [(0, 1)]
    assert graph.nodes[2].degree == 0
    assert graph.nodes[2].two_qubit_gate_count == 0
    assert graph.nodes[2].first_active_depth == 1
    assert graph.nodes[3].first_active_depth is None


def test_graph_objective_equals_gate_level_objective_for_every_valid_toy_partition() -> None:
    circuit = make_six_qubit_toy_circuit()
    graph = build_interaction_graph(circuit)
    partitions = tuple(valid_two_fragment_partitions(circuit.num_qubits, qmax=3))
    assert len(partitions) == 10
    for partition in partitions:
        assert isclose(
            graph_partition_objective(graph, partition),
            gate_level_partition_objective(circuit, partition),
            abs_tol=1e-12,
        )
    assert isclose(graph_partition_objective(graph, (0, 0, 0, 1, 1, 1)), log(81), abs_tol=1e-12)


def test_graph_serialization_is_deterministic() -> None:
    circuit = make_six_qubit_toy_circuit()
    assert build_interaction_graph(circuit).as_dict() == build_interaction_graph(circuit).as_dict()
