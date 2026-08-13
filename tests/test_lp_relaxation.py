from math import ceil, isclose
import random

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition
from certicut.optimization.lp import solve_lp_relaxation


def test_lp_relaxation_is_a_valid_lower_bound_on_100_seeded_instances() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        num_qubits = generator.randint(4, 8)
        circuit = QuantumCircuit(num_qubits)
        for _ in range(generator.randint(1, 2 * num_qubits)):
            circuit.cx(*generator.sample(range(num_qubits), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(num_qubits / 2)
        lp = solve_lp_relaxation(graph, qmax=qmax, exact_num_fragments=True)
        exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert lp.status == exact.status == "optimal"
        assert lp.lower_bound_log is not None
        assert exact.objective_log_cost is not None
        assert lp.lower_bound_log <= exact.objective_log_cost + 1e-10


def test_lp_obeys_fixed_assignments() -> None:
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)
    circuit.cx(2, 3)
    result = solve_lp_relaxation(
        build_interaction_graph(circuit), qmax=2, exact_num_fragments=True, fixed_assignments={1: 1}
    )
    assert result.status == "optimal"
    assert result.assignments is not None
    assert isclose(result.assignments[0][0], 1.0, abs_tol=1e-12)
    assert isclose(result.assignments[1][1], 1.0, abs_tol=1e-12)
