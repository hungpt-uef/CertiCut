from math import ceil, isclose
import random

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition
from certicut.optimization.lp import solve_b2_separated_lp, solve_lp_variant


def test_b2s_reproduces_all_triangle_b2_on_100_oracle_instances() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        full = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=True, variant="b2_metric")
        separated = solve_b2_separated_lp(graph, qmax=qmax, exact_num_fragments=True)
        exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert isclose(full.lower_bound_log or 0, separated.relaxation.lower_bound_log or 0, abs_tol=1e-9)
        assert (separated.relaxation.lower_bound_log or 0) <= (exact.objective_log_cost or 0) + 1e-10


def test_b2s_top_k_reaches_same_bound_as_all_violated_on_toy_scale() -> None:
    circuit = QuantumCircuit(8)
    for u in range(8):
        circuit.cx(u, (u + 1) % 8)
        circuit.cx(u, (u + 3) % 8)
    graph = build_interaction_graph(circuit)
    all_cuts = solve_b2_separated_lp(graph, qmax=4, exact_num_fragments=True)
    top_k = solve_b2_separated_lp(graph, qmax=4, exact_num_fragments=True, policy="top_k", top_k=10)
    assert isclose(all_cuts.relaxation.lower_bound_log or 0, top_k.relaxation.lower_bound_log or 0, abs_tol=1e-9)
