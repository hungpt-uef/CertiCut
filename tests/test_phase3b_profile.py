from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb


def test_profile_collects_baseline_metrics_without_changing_certificate() -> None:
    graph = build_interaction_graph(make_benchmark_circuit("community", 8, 7))
    result = solve_certified_bnb(
        graph, qmax=4, exact_num_fragments=True, node_limit=3, collect_profile=True
    )
    assert result.status in {"optimal", "node_limit"}
    assert result.certificate is not None
    assert result.profile is not None
    assert result.profile.lp_solve_count >= 1
    assert result.profile.generated_nodes >= 0
    assert result.profile.root_lp_lb <= result.certificate.upper_bound_log + 1e-10
    assert result.profile.max_frontier_size >= 1


def test_benchmark_families_build_optimizer_only_cnot_circuits() -> None:
    for family in ("random", "nearest_neighbor", "qaoa_ring", "dense", "community"):
        circuit = make_benchmark_circuit(family, 8, 3)
        assert circuit.num_qubits == 8
        assert circuit.size() > 0
        assert all(instruction.operation.name == "cx" for instruction in circuit.data)
