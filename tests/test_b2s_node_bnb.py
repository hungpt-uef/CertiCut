from math import ceil, isclose
import random

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def test_b2s_node_matches_oracle_and_maintains_pool_profile() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        result = solve_certified_bnb(
            graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_node",
            node_separation_top_k=20, node_separation_max_rounds=2, collect_profile=True,
        )
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert result.certificate is not None and result.certificate.proven_optimal
        assert isclose(result.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
        assert result.profile is not None
        assert result.profile.pool_version_final >= 0


def test_b2s_node_node_limit_certificate_remains_safe() -> None:
    circuit = QuantumCircuit(8)
    for u in range(8):
        for v in range(u + 1, 8):
            if (u + v) % 2:
                circuit.cx(u, v)
    graph = build_interaction_graph(circuit)
    result = solve_certified_bnb(
        graph, qmax=4, exact_num_fragments=True, node_limit=1, lp_variant="b2s_node"
    )
    oracle = solve_exact_partition(graph, num_fragments=2, qmax=4, exact_num_fragments=True)
    assert result.certificate is not None
    assert result.certificate.lower_bound_log <= (oracle.objective_log_cost or 0) + 1e-10
    assert (oracle.objective_log_cost or 0) <= result.certificate.upper_bound_log + 1e-10


def test_global_cut_pool_canonicalizes_duplicate_child_cuts() -> None:
    circuit = QuantumCircuit(8)
    for u in range(8):
        circuit.cx(u, (u + 1) % 8)
        circuit.cx(u, (u + 3) % 8)
    result = solve_certified_bnb(
        build_interaction_graph(circuit), qmax=4, exact_num_fragments=True,
        lp_variant="b2s_node", node_separation_top_k=100, node_separation_max_rounds=3,
        collect_profile=True,
    )
    assert result.profile is not None
    assert result.profile.pool_version_final <= result.profile.root_cuts_added + result.profile.cuts_discovered_nodes + 1
