from math import ceil, isclose, log
import random

from qiskit import QuantumCircuit

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import brute_force_exact_partition, solve_exact_partition


def test_milp_matches_phase0_toy_ground_truth_and_cut_metadata() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    solution = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    assert solution.status == "optimal"
    assert solution.partition == (0, 0, 0, 1, 1, 1)
    assert solution.fragments == ((0, 1, 2), (3, 4, 5))
    assert solution.cut_edges == ((1, 4), (2, 3))
    assert solution.cut_instruction_indices == (4, 5)
    assert isclose(solution.objective_log_cost or 0, log(81), abs_tol=1e-10)
    assert isclose(solution.gamma or 0, 81, abs_tol=1e-10)


def test_milp_uses_aggregated_edge_weight() -> None:
    circuit = QuantumCircuit(2)
    for _ in range(3):
        circuit.cx(0, 1)
    graph = build_interaction_graph(circuit)
    solution = solve_exact_partition(graph, num_fragments=2, qmax=1, exact_num_fragments=True)
    assert solution.cut_edges == ((0, 1),)
    assert solution.cut_instruction_indices == (0, 1, 2)
    assert isclose(solution.objective_log_cost or 0, 3 * log(9), abs_tol=1e-10)
    assert isclose(solution.gamma or 0, 729, abs_tol=1e-10)


def test_at_most_and_exact_fragment_semantics_are_explicit() -> None:
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)
    graph = build_interaction_graph(circuit)
    at_most = solve_exact_partition(graph, num_fragments=2, qmax=4)
    exactly = solve_exact_partition(graph, num_fragments=2, qmax=4, exact_num_fragments=True)
    assert at_most.fragments == ((0, 1, 2, 3), ())
    assert at_most.objective_log_cost == 0
    assert exactly.status == "optimal"
    assert all(exactly.fragments)


def test_capacity_infeasibility_returns_clean_result() -> None:
    graph = build_interaction_graph(QuantumCircuit(7))
    solution = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    assert solution.status == "infeasible"
    assert solution.partition is None
    assert solution.objective_log_cost is None


def test_isolated_qubits_are_assigned_under_capacity_constraints() -> None:
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)
    graph = build_interaction_graph(circuit)
    solution = solve_exact_partition(graph, num_fragments=2, qmax=2, exact_num_fragments=True)
    assert solution.status == "optimal"
    assert solution.partition is not None
    assert len(solution.partition) == 4
    assert all(len(fragment) <= 2 for fragment in solution.fragments)
    assert sorted(qubit for fragment in solution.fragments for qubit in fragment) == [0, 1, 2, 3]


def test_canonical_symmetry_breaking_is_deterministic() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    first = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    second = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    assert first.as_dict() == second.as_dict()
    assert first.partition is not None
    assert first.partition[0] == 0


def test_milp_matches_brute_force_on_100_deterministic_random_circuits() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        num_qubits = generator.randint(4, 8)
        circuit = QuantumCircuit(num_qubits)
        for _ in range(generator.randint(1, 2 * num_qubits)):
            control, target = generator.sample(range(num_qubits), 2)
            circuit.cx(control, target)
        graph = build_interaction_graph(circuit)
        qmax = ceil(num_qubits / 2)
        milp_solution = solve_exact_partition(
            graph, num_fragments=2, qmax=qmax, exact_num_fragments=True
        )
        brute_force_solution = brute_force_exact_partition(
            graph, num_fragments=2, qmax=qmax, exact_num_fragments=True
        )
        assert milp_solution.status == brute_force_solution.status == "optimal"
        assert isclose(
            milp_solution.objective_log_cost or 0,
            brute_force_solution.objective_log_cost or 0,
            abs_tol=1e-10,
        )
