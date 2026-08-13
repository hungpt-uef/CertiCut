"""Track A exact-balanced graph baselines with no lower-bound certificate."""

from __future__ import annotations

from time import perf_counter

from certicut.baselines.common import BaselineResult, safe_overhead
from certicut.graph.interaction import InteractionGraph
from certicut.optimization.heuristics import warm_start_partition


def solve_graph_heuristic(graph: InteractionGraph, *, qmax: int, variant: str) -> BaselineResult:
    """Run H2/H3 under the exact balanced two-fragment Track A regime."""
    started = perf_counter()
    solution = warm_start_partition(graph, qmax=qmax, exact_num_fragments=True, variant=variant)
    runtime = perf_counter() - started
    if solution is None:
        return BaselineResult(f"graph_{variant}", "A_exact_balanced", "infeasible", runtime, None, None, (), (), None, "heuristic found no feasible partition")
    partition, objective = solution
    return BaselineResult(
        f"graph_{variant}", "A_exact_balanced", "feasible", runtime, objective, safe_overhead(objective),
        tuple(index for edge in graph.edges if partition[edge.u] != partition[edge.v] for index in edge.instruction_indices),
        tuple(partition.count(label) for label in (0, 1)), None,
        "Heuristic only: no quantitative lower bound or optimality certificate.",
    )
