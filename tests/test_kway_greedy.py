from qiskit import QuantumCircuit

from certicut.baselines.kway_greedy import solve_weighted_kway_greedy
from certicut.graph.interaction import build_interaction_graph, graph_partition_objective


def test_weighted_kway_greedy_is_capacity_exact_and_deterministic() -> None:
    circuit = QuantumCircuit(8)
    for qubit in range(8):
        circuit.cx(qubit, (qubit + 1) % 8)
    graph = build_interaction_graph(circuit)
    first = solve_weighted_kway_greedy(graph, capacities=(3, 3, 2), seed=7)
    second = solve_weighted_kway_greedy(graph, capacities=(3, 3, 2), seed=7)
    partition, objective, _ = first
    assert tuple(partition.count(fragment) for fragment in range(3)) == (3, 3, 2)
    assert objective == graph_partition_objective(graph, partition)
    assert first[:2] == second[:2]
