from math import ceil, isclose
import random

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph, graph_partition_objective
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition
from certicut.optimization.heuristics import warm_start_partition


def test_all_warm_starts_are_feasible_deterministic_and_not_worse_than_h0() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        h0 = warm_start_partition(graph, qmax=qmax, exact_num_fragments=True, variant="h0")
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert h0 is not None
        for variant in ("h0", "h1", "h2", "h3"):
            candidate = warm_start_partition(graph, qmax=qmax, exact_num_fragments=True, variant=variant)
            assert candidate is not None
            partition, objective = candidate
            assert partition[0] == 0
            assert sorted(partition.count(label) for label in (0, 1)) == [n // 2, (n + 1) // 2]
            assert isclose(objective, graph_partition_objective(graph, partition), abs_tol=1e-10)
            assert (oracle.objective_log_cost or 0) <= objective + 1e-10
            assert objective <= h0[1] + 1e-10
            assert candidate == warm_start_partition(graph, qmax=qmax, exact_num_fragments=True, variant=variant)


def test_bnb_completion_correctness_is_independent_of_warm_start() -> None:
    generator = random.Random(20260810)
    for _ in range(40):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            circuit.cx(*generator.sample(range(n), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(n / 2)
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        for variant in ("h0", "h1", "h2", "h3"):
            result = solve_certified_bnb(
                graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant=variant
            )
            assert result.certificate is not None and result.certificate.proven_optimal
            assert isclose(result.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
