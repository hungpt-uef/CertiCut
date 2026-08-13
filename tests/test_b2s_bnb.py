from math import isclose
from math import ceil
import random

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


WITNESS_EDGES = (
    (0, 2, 1), (0, 3, 3), (0, 4, 5), (0, 6, 1), (0, 7, 5),
    (1, 7, 2), (2, 5, 1), (2, 6, 5), (2, 7, 1), (3, 4, 1),
    (3, 5, 3), (4, 5, 4), (4, 7, 1), (5, 7, 5),
)


def _witness_graph():
    circuit = QuantumCircuit(8)
    for control, target, count in WITNESS_EDGES:
        for _ in range(count):
            circuit.cx(control, target)
    return build_interaction_graph(circuit)


def test_b2s_root_pool_completes_fractional_witness_with_exact_certificate() -> None:
    graph = _witness_graph()
    result = solve_certified_bnb(
        graph, qmax=4, exact_num_fragments=True, collect_profile=True, lp_variant="b2s_root"
    )
    oracle = solve_exact_partition(graph, num_fragments=2, qmax=4, exact_num_fragments=True)
    assert result.status == "optimal"
    assert result.certificate is not None and result.certificate.proven_optimal
    assert isclose(result.certificate.lower_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
    assert result.profile is not None
    assert result.profile.root_cuts_added > 0
    assert result.profile.node_lp_solve_count > 0


def test_b2s_root_pool_timeout_certificate_contains_witness_optimum() -> None:
    graph = _witness_graph()
    result = solve_certified_bnb(
        graph, qmax=4, exact_num_fragments=True, node_limit=0, lp_variant="b2s_root"
    )
    oracle = solve_exact_partition(graph, num_fragments=2, qmax=4, exact_num_fragments=True)
    assert result.status == "node_limit"
    assert result.certificate is not None
    assert result.certificate.lower_bound_log <= (oracle.objective_log_cost or 0) + 1e-10
    assert (oracle.objective_log_cost or 0) <= result.certificate.upper_bound_log + 1e-10


def test_b2s_root_pool_bnb_matches_oracle_on_100_small_instances() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        result = solve_certified_bnb(
            graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_root"
        )
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert result.certificate is not None and result.certificate.proven_optimal
        assert isclose(result.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
