from math import isclose

from qiskit import QuantumCircuit

from certicut.baselines.restricted_exact import solve_restricted_gate_only_exact
from certicut.graph.interaction import build_interaction_graph, gate_level_partition_objective, graph_partition_objective


def test_restricted_exact_direct_gate_sum_matches_graph_sum() -> None:
    circuit = QuantumCircuit(6)
    circuit.cx(0, 1)
    circuit.iswap(1, 2)
    circuit.rzz(0.5, 2, 3)
    circuit.cz(3, 4)
    circuit.cx(4, 5)
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    result = solve_restricted_gate_only_exact(graph, capacities=(3, 3))
    assert isclose(result.direct_gate_log_cost, result.graph_log_cost, abs_tol=1e-10)
    assert isclose(result.graph_log_cost, graph_partition_objective(graph, result.partition), abs_tol=1e-10)
    assert isclose(
        result.direct_gate_log_cost,
        gate_level_partition_objective(circuit, result.partition, cost_model="qiskit_qpd"),
        abs_tol=1e-10,
    )
