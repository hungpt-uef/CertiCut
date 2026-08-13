from math import log

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.k_partition import solve_lexicographic_k_partition


def test_lexicographic_stage_respects_sampling_budget() -> None:
    circuit = QuantumCircuit(6)
    for first, second in ((0, 1), (1, 2), (3, 4), (4, 5), (0, 5), (2, 3)):
        circuit.cx(first, second)
    graph = build_interaction_graph(circuit)
    result = solve_lexicographic_k_partition(
        graph,
        num_fragments=2,
        lower_capacities=(3, 3),
        upper_capacities=(3, 3),
        routing_costs=tuple(max(0, abs(edge.u - edge.v) - 1) for edge in graph.edges),
        allowed_gamma_factor=1.05,
    )
    assert result.partition is not None
    assert result.objective_log_cost is not None
    assert result.sampling_optimum.objective_log_cost is not None
    assert result.objective_log_cost <= result.sampling_optimum.objective_log_cost + log(1.05) + 1e-9
    assert result.routing_surrogate_cost is not None


def test_lexicographic_rejects_invalid_budget_and_routing_vector() -> None:
    graph = build_interaction_graph(QuantumCircuit(2))
    try:
        solve_lexicographic_k_partition(
            graph, num_fragments=2, lower_capacities=(1, 1), upper_capacities=(1, 1),
            routing_costs=(), allowed_gamma_factor=0.99,
        )
    except ValueError as error:
        assert "allowed_gamma_factor" in str(error)
    else:
        raise AssertionError("invalid budget was accepted")
