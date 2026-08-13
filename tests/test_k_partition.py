from itertools import product
from math import isclose

from qiskit import QuantumCircuit

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph, fixed_capacity_cross_pair_count, graph_partition_objective
from certicut.optimization.k_partition import solve_scip_k_partition


def test_k2_scip_matches_existing_balanced_toy_optimum() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    result = solve_scip_k_partition(
        graph, num_fragments=2, lower_capacities=(3, 3), upper_capacities=(3, 3)
    )
    assert result.status == "optimal"
    assert result.partition is not None
    assert tuple(map(len, result.fragments)) == (3, 3)
    assert isclose(result.objective_log_cost or 0.0, graph_partition_objective(graph, (0, 0, 0, 1, 1, 1)))
    assert result.certificate is not None and result.certificate.proven_optimal
    assert result.certificate.certificate_kind == "solver_tolerance"


def test_k3_heterogeneous_capacities_matches_exhaustive_oracle() -> None:
    circuit = QuantumCircuit(7)
    for control, target in ((0, 1), (1, 2), (0, 2), (3, 4), (3, 5), (4, 5), (2, 3), (5, 6)):
        circuit.cx(control, target)
    graph = build_interaction_graph(circuit)
    lower, upper = (3, 2, 2), (3, 2, 2)
    result = solve_scip_k_partition(
        graph, num_fragments=3, lower_capacities=lower, upper_capacities=upper
    )
    oracle = min(
        graph_partition_objective(graph, partition)
        for partition in product(range(3), repeat=graph.num_qubits)
        if tuple(partition.count(fragment) for fragment in range(3)) == upper
    )
    assert result.status == "optimal"
    assert result.partition is not None
    assert tuple(map(len, result.fragments)) == upper
    assert isclose(result.objective_log_cost or 0.0, oracle, abs_tol=1e-10)
    assert result.certificate is not None and result.certificate.proven_optimal


def test_capacity_infeasibility_returns_no_false_certificate() -> None:
    graph = build_interaction_graph(QuantumCircuit(5))
    result = solve_scip_k_partition(
        graph, num_fragments=3, lower_capacities=(2, 2, 2), upper_capacities=(3, 3, 3)
    )
    assert result.status == "infeasible"
    assert result.partition is None
    assert result.certificate is None


def test_fixed_capacity_cross_pair_identity_generalizes_balanced_bisection() -> None:
    assert fixed_capacity_cross_pair_count((3, 3)) == 9
    assert fixed_capacity_cross_pair_count((4, 3, 3)) == 33


def test_exact_capacity_strengthening_preserves_optimum() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    plain = solve_scip_k_partition(
        graph, num_fragments=3, lower_capacities=(2, 2, 2), upper_capacities=(2, 2, 2),
        cross_pair_strengthening=False, symmetry_breaking=False,
    )
    strengthened = solve_scip_k_partition(
        graph, num_fragments=3, lower_capacities=(2, 2, 2), upper_capacities=(2, 2, 2),
    )
    assert plain.objective_log_cost == strengthened.objective_log_cost
    assert strengthened.certificate is not None and strengthened.certificate.proven_optimal
