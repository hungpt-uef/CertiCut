from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.scip_core import solve_scip_core


def test_scip_core_variants_return_ordered_primal_dual_bounds():
    graph = build_interaction_graph(make_benchmark_circuit("random", 8, 3))
    for variant in ("g0_basic", "g1_cardinality", "g2_b2s"):
        result = solve_scip_core(graph, variant=variant, time_limit_s=2.0)
        assert result.primal_bound is not None
        assert result.dual_bound is not None
        assert result.dual_bound <= result.primal_bound + 1e-9
