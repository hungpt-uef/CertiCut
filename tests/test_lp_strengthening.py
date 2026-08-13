from itertools import combinations
from math import ceil, isclose
import random

from qiskit import QuantumCircuit

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition
from certicut.optimization.lp import solve_lp_variant


def test_b1_compact_matches_b0_bound_and_reduces_variables() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    b0 = solve_lp_variant(graph, qmax=3, exact_num_fragments=True, variant="b0")
    b1 = solve_lp_variant(graph, qmax=3, exact_num_fragments=True, variant="b1_compact")
    assert isclose(b0.lower_bound_log or 0, b1.lower_bound_log or 0, abs_tol=1e-10)
    assert b1.variable_count < b0.variable_count


def test_b2_cardinality_equality_and_triangles_hold_for_all_toy_partitions() -> None:
    circuit = make_six_qubit_toy_circuit()
    for first in combinations(range(1, 6), 2):
        partition = {0, *first}
        cuts = {(min(i, j), max(i, j)): int((i in partition) != (j in partition)) for i, j in combinations(range(6), 2)}
        assert sum(cuts.values()) == 9
        for i, j, k in combinations(range(6), 3):
            ij, ik, jk = cuts[(i, j)], cuts[(i, k)], cuts[(j, k)]
            assert ij <= ik + jk and ik <= ij + jk and jk <= ij + ik
            assert ij + ik + jk <= 2


def test_b1_b2_bounds_are_valid_and_b2_is_not_weaker_on_100_instances() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        b0 = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=True, variant="b0")
        b1 = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=True, variant="b1_compact")
        b2 = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=True, variant="b2_metric")
        assert isclose(b0.lower_bound_log or 0, b1.lower_bound_log or 0, abs_tol=1e-10)
        assert (b2.lower_bound_log or 0) + 1e-10 >= (b0.lower_bound_log or 0)
        assert (b2.lower_bound_log or 0) <= (exact.objective_log_cost or 0) + 1e-10


def test_b2_bnb_matches_oracle_on_100_instances() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        result = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2_metric")
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert result.certificate is not None and result.certificate.proven_optimal
        assert isclose(result.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)


def test_b1_bnb_matches_oracle_and_b2_node_limit_certificate_is_safe() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        b1 = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, lp_variant="b1_compact")
        b2_limited = solve_certified_bnb(
            graph, qmax=qmax, exact_num_fragments=True, node_limit=0, lp_variant="b2_metric"
        )
        assert b1.certificate is not None and b1.certificate.proven_optimal
        assert isclose(b1.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
        assert b2_limited.certificate is not None
        assert b2_limited.certificate.lower_bound_log <= (oracle.objective_log_cost or 0) + 1e-10
        assert (oracle.objective_log_cost or 0) <= b2_limited.certificate.upper_bound_log + 1e-10
