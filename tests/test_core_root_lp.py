from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.core_root_lp import solve_core_root_lp
from certicut.optimization.exact import brute_force_exact_partition


def test_root_polyhedral_variants_have_ordered_valid_bounds():
    graph = build_interaction_graph(make_benchmark_circuit("weighted_random", 8, 3))
    optimum = brute_force_exact_partition(graph, num_fragments=2, qmax=4, exact_num_fragments=True)
    values = {
        variant: solve_core_root_lp(graph, variant=variant)
        for variant in ("b0", "cardinality", "triangles", "b2s")
    }
    assert values["b0"].lower_bound <= values["cardinality"].lower_bound + 1e-9
    assert values["b0"].lower_bound <= values["triangles"].lower_bound + 1e-9
    assert values["cardinality"].lower_bound <= values["b2s"].lower_bound + 1e-9
    assert values["triangles"].lower_bound <= values["b2s"].lower_bound + 1e-9
    assert all(value.lower_bound <= optimum.objective_log_cost + 1e-9 for value in values.values())
