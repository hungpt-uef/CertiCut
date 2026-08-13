from math import ceil, isclose
import random

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def test_strong_branching_matches_oracle_and_records_scores() -> None:
    generator = random.Random(20260810)
    recorded = 0
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        result = solve_certified_bnb(
            graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant="h2",
            branching_rule="strong", strong_branching_k=4, collect_profile=True, collect_strong_branching_states=True,
        )
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert result.certificate is not None and result.certificate.proven_optimal
        assert isclose(result.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
        for state in result.strong_branching_states:
            assert str(state["selected_variable"]) in state["candidate_scores"]
            assert "0" not in state["candidate_scores"]
            assert state["probe_time_s"] >= 0
            recorded += 1
    assert recorded >= 0


def test_strong_branching_node_limit_certificate_and_determinism() -> None:
    circuit = QuantumCircuit(8)
    for u in range(8):
        for v in range(u + 1, 8):
            if (u + 2 * v) % 3:
                circuit.cx(u, v)
    graph = build_interaction_graph(circuit)
    first = solve_certified_bnb(
        graph, qmax=4, exact_num_fragments=True, node_limit=2, lp_variant="b2s_root", warm_start_variant="h2",
        branching_rule="strong", strong_branching_k=4, collect_profile=True, collect_strong_branching_states=True,
    )
    second = solve_certified_bnb(
        graph, qmax=4, exact_num_fragments=True, node_limit=2, lp_variant="b2s_root", warm_start_variant="h2",
        branching_rule="strong", strong_branching_k=4, collect_profile=True, collect_strong_branching_states=True,
    )
    oracle = solve_exact_partition(graph, num_fragments=2, qmax=4, exact_num_fragments=True)
    assert first.certificate is not None
    assert first.certificate.lower_bound_log <= (oracle.objective_log_cost or 0) + 1e-10
    assert (oracle.objective_log_cost or 0) <= first.certificate.upper_bound_log + 1e-10
    assert first.status == second.status
    assert first.partition == second.partition
    assert first.certificate == second.certificate
    assert first.expanded_nodes == second.expanded_nodes
    assert first.strong_branching_states == second.strong_branching_states
