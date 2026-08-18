from math import isclose

from qiskit import QuantumCircuit

from certicut.baselines.kway_kl import _kl_pair_pass, _objective, solve_kway_kl
from certicut.evaluation.canonical import evaluate_independent_qpd
from certicut.graph.interaction import build_interaction_graph, gate_level_partition_objective


def _heterogeneous_graph():
    circuit = QuantumCircuit(8)
    circuit.cx(0, 1)
    circuit.iswap(1, 2)
    circuit.cx(2, 3)
    circuit.rzz(0.4, 3, 4)
    circuit.cz(4, 5)
    circuit.iswap(5, 6)
    circuit.cx(6, 7)
    circuit.rzz(0.8, 7, 0)
    return circuit, build_interaction_graph(circuit, cost_model="qiskit_qpd")


def test_kway_kl_preserves_capacity_and_seed() -> None:
    _, graph = _heterogeneous_graph()
    first = solve_kway_kl(graph, capacities=(3, 3, 2), weight_mode="qpd", seed=9, restarts=3)
    second = solve_kway_kl(graph, capacities=(3, 3, 2), weight_mode="qpd", seed=9, restarts=3)
    assert first.partition is not None
    assert first.fragment_sizes == (3, 3, 2)
    assert first.partition == second.partition
    assert first.objective_log_cost == second.objective_log_cost


def test_kl_objective_uses_canonical_qpd_evaluator() -> None:
    circuit, graph = _heterogeneous_graph()
    result = solve_kway_kl(graph, capacities=(3, 3, 2), weight_mode="count", seed=1)
    assert result.partition is not None
    evaluation = evaluate_independent_qpd(graph, result.partition, (3, 3, 2))
    assert result.objective_log_cost == evaluation.objective_log_cost
    assert isclose(
        evaluation.objective_log_cost,
        gate_level_partition_objective(circuit, result.partition, cost_model="qiskit_qpd"),
        abs_tol=1e-10,
    )


def test_kl_pass_can_accept_an_uphill_first_swap() -> None:
    _, graph = _heterogeneous_graph()
    initial = (0, 0, 0, 1, 1, 1, 2, 2)
    result = _kl_pair_pass(graph, initial, 0, 1, "qpd")
    assert _objective(graph, result, "qpd") <= _objective(graph, initial, "qpd")
