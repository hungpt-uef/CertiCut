"""Capacitated K-way independent-QPD partitioning with SCIP tolerance bounds."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, log
import sys
from time import perf_counter
from typing import Any, Sequence

from pyscipopt import Model, quicksum

from certicut.graph.interaction import InteractionGraph, fixed_capacity_cross_pair_count, graph_partition_objective
from certicut.optimization.certificate import Certificate, make_certificate
from certicut.optimization.scip_core import SCIP_TOLERANCE_LABEL


@dataclass(frozen=True)
class KPartitionResult:
    """SCIP solution, assignment witness, and solver-tolerance bound report."""

    status: str
    num_fragments: int
    lower_capacities: tuple[int, ...]
    upper_capacities: tuple[int, ...]
    partition: tuple[int, ...] | None
    fragments: tuple[tuple[int, ...], ...]
    cut_edges: tuple[tuple[int, int], ...]
    cut_instruction_indices: tuple[int, ...]
    objective_log_cost: float | None
    gamma: float | None
    certificate: Certificate | None
    nodes: int
    lp_iterations: int
    runtime_s: float
    bound_status: str
    tolerance: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LexicographicKPartitionResult:
    """Sampling-first then routing-surrogate solution under a multiplicative budget."""

    sampling_optimum: KPartitionResult
    routing_status: str
    partition: tuple[int, ...] | None
    fragments: tuple[tuple[int, ...], ...]
    objective_log_cost: float | None
    gamma: float | None
    routing_surrogate_cost: float | None
    allowed_log_cost: float
    allowed_gamma_factor: float
    runtime_s: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def solve_scip_k_partition(
    graph: InteractionGraph,
    *,
    num_fragments: int,
    lower_capacities: Sequence[int] | None = None,
    upper_capacities: Sequence[int] | None = None,
    time_limit_s: float | None = None,
    cross_pair_strengthening: bool = False,
    metric_strengthening: bool = False,
    symmetry_breaking: bool = True,
) -> KPartitionResult:
    """Minimize independent-QPD log overhead under per-fragment capacities.

    ``y[e, k]`` is one iff both endpoints of edge ``e`` occupy fragment ``k``;
    therefore ``z[e] + sum_k(y[e, k]) == 1`` exactly identifies a cut edge.
    Default capacities require every fragment and permit near-balanced sizes.
    Pass explicit bounds for heterogeneous devices or empty fragments. For exact
    Equal exact capacities fix qubit zero in fragment zero to remove equivalent
    label permutations. Optional all-pair cardinality and metric extensions are
    valid but dense; they are disabled by default after their ablation showed
    poor end-to-end behavior at the E9 scale.
    """
    lower, upper = _capacities(graph.num_qubits, num_fragments, lower_capacities, upper_capacities)
    if time_limit_s is not None and time_limit_s < 0:
        raise ValueError("time_limit_s must be nonnegative")
    if sum(lower) > graph.num_qubits or sum(upper) < graph.num_qubits:
        return _infeasible_result(num_fragments, lower, upper)

    model = Model("certicut_k_partition")
    started = perf_counter()
    model.hideOutput(True)
    model.setIntParam("randomization/randomseedshift", 0)
    model.setIntParam("randomization/permutationseed", 0)
    if time_limit_s is not None:
        model.setRealParam("limits/time", time_limit_s)

    n = graph.num_qubits
    x = {(qubit, fragment): model.addVar(vtype="B", name=f"x_{qubit}_{fragment}")
         for qubit in range(n) for fragment in range(num_fragments)}
    z = {edge_index: model.addVar(vtype="B", name=f"z_{edge_index}")
         for edge_index in range(len(graph.edges))}
    y = {(edge_index, fragment): model.addVar(vtype="B", name=f"y_{edge_index}_{fragment}")
         for edge_index in range(len(graph.edges)) for fragment in range(num_fragments)}

    for qubit in range(n):
        model.addCons(quicksum(x[qubit, fragment] for fragment in range(num_fragments)) == 1)
    for fragment in range(num_fragments):
        load = quicksum(x[qubit, fragment] for qubit in range(n))
        model.addCons(load >= lower[fragment])
        model.addCons(load <= upper[fragment])
    for edge_index, edge in enumerate(graph.edges):
        for fragment in range(num_fragments):
            model.addCons(y[edge_index, fragment] <= x[edge.u, fragment])
            model.addCons(y[edge_index, fragment] <= x[edge.v, fragment])
            model.addCons(y[edge_index, fragment] >= x[edge.u, fragment] + x[edge.v, fragment] - 1)
        model.addCons(z[edge_index] + quicksum(y[edge_index, fragment] for fragment in range(num_fragments)) == 1)
    _add_exact_capacity_strengthening(
        model, graph, x, z, num_fragments, lower, upper,
        cross_pair_strengthening=cross_pair_strengthening, metric_strengthening=metric_strengthening,
        symmetry_breaking=symmetry_breaking,
    )
    model.setObjective(
        quicksum(edge.qpd_log_cost * z[edge_index] for edge_index, edge in enumerate(graph.edges)),
        "minimize",
    )
    model.optimize()

    status = str(model.getStatus())
    tolerance = float(model.getParam("numerics/feastol"))
    primal = _finite_bound(model.getPrimalbound())
    dual = _finite_bound(model.getDualbound())
    solution = model.getBestSol() if primal is not None else None
    partition = (
        tuple(
            next(fragment for fragment in range(num_fragments) if model.getSolVal(solution, x[qubit, fragment]) > 0.5)
            for qubit in range(n)
        )
        if solution is not None
        else None
    )
    certificate = (
        make_certificate(dual, primal, tolerance=tolerance, certificate_kind="solver_tolerance")
        if primal is not None and dual is not None and dual <= primal + tolerance
        else None
    )
    return _result(
        graph, status, num_fragments, lower, upper, partition, certificate,
        int(model.getNNodes()), int(model.getNLPIterations()), perf_counter() - started,
        SCIP_TOLERANCE_LABEL if certificate is not None else "no finite SCIP bound pair", tolerance,
    )


def solve_lexicographic_k_partition(
    graph: InteractionGraph,
    *,
    num_fragments: int,
    lower_capacities: Sequence[int],
    upper_capacities: Sequence[int],
    routing_costs: Sequence[float],
    allowed_gamma_factor: float = 1.05,
    time_limit_s: float | None = None,
    cross_pair_strengthening: bool = False,
    metric_strengthening: bool = False,
    symmetry_breaking: bool = True,
) -> LexicographicKPartitionResult:
    """Minimize routing surrogate without exceeding a sampling-overhead budget.

    Stage one obtains the independent-QPD optimum. Stage two constrains the same
    log objective to ``J* + log(allowed_gamma_factor)`` and minimizes the cost
    of interactions retained inside fragments. ``routing_costs[e]`` is an
    explicit user-supplied local-routing surrogate; no global mapping claim.
    """
    if allowed_gamma_factor < 1:
        raise ValueError("allowed_gamma_factor must be at least one")
    if len(routing_costs) != len(graph.edges) or any(cost < 0 for cost in routing_costs):
        raise ValueError("routing_costs must contain one nonnegative value per graph edge")
    started = perf_counter()
    first = solve_scip_k_partition(
        graph, num_fragments=num_fragments, lower_capacities=lower_capacities,
        upper_capacities=upper_capacities, time_limit_s=time_limit_s,
        cross_pair_strengthening=cross_pair_strengthening, metric_strengthening=metric_strengthening,
        symmetry_breaking=symmetry_breaking,
    )
    if first.partition is None or first.objective_log_cost is None:
        return LexicographicKPartitionResult(first, first.status, None, (), None, None, None, float("inf"), allowed_gamma_factor, perf_counter() - started)
    remaining = max(0.0, time_limit_s - (perf_counter() - started)) if time_limit_s is not None else None
    allowed = first.objective_log_cost + log(allowed_gamma_factor)
    lower, upper = _capacities(graph.num_qubits, num_fragments, lower_capacities, upper_capacities)
    model = Model("certicut_k_partition_lexicographic")
    model.hideOutput(True)
    model.setIntParam("randomization/randomseedshift", 0)
    model.setIntParam("randomization/permutationseed", 0)
    if remaining is not None:
        model.setRealParam("limits/time", remaining)
    x, z, y = _add_k_partition_variables(model, graph, num_fragments, lower, upper)
    _add_exact_capacity_strengthening(
        model, graph, x, z, num_fragments, lower, upper,
        cross_pair_strengthening=cross_pair_strengthening, metric_strengthening=metric_strengthening,
        symmetry_breaking=symmetry_breaking,
    )
    sampling = quicksum(edge.qpd_log_cost * z[index] for index, edge in enumerate(graph.edges))
    # solver tolerance is explicitly widened before imposing stage-two budget.
    model.addCons(sampling <= allowed + float(model.getParam("numerics/feastol")))
    model.setObjective(quicksum(routing_costs[index] * y[index, fragment] for index in range(len(graph.edges)) for fragment in range(num_fragments)), "minimize")
    model.optimize()
    solution = model.getBestSol()
    partition = (
        tuple(next(fragment for fragment in range(num_fragments) if model.getSolVal(solution, x[qubit, fragment]) > 0.5) for qubit in range(graph.num_qubits))
        if solution is not None else None
    )
    objective = graph_partition_objective(graph, partition) if partition is not None else None
    routing = float(model.getObjVal()) if solution is not None else None
    fragments = tuple(tuple(qubit for qubit, label in enumerate(partition) if label == fragment) for fragment in range(num_fragments)) if partition is not None else ()
    return LexicographicKPartitionResult(
        first, str(model.getStatus()), partition, fragments, objective, _safe_gamma(objective) if objective is not None else None,
        routing, allowed, allowed_gamma_factor, perf_counter() - started,
    )


def _add_k_partition_variables(
    model: Model, graph: InteractionGraph, num_fragments: int, lower: tuple[int, ...], upper: tuple[int, ...]
) -> tuple[dict[tuple[int, int], Any], dict[int, Any], dict[tuple[int, int], Any]]:
    """Add the shared exact K-way assignment/locality formulation."""
    n = graph.num_qubits
    x = {(qubit, fragment): model.addVar(vtype="B", name=f"x_{qubit}_{fragment}") for qubit in range(n) for fragment in range(num_fragments)}
    z = {edge_index: model.addVar(vtype="B", name=f"z_{edge_index}") for edge_index in range(len(graph.edges))}
    y = {(edge_index, fragment): model.addVar(vtype="B", name=f"y_{edge_index}_{fragment}") for edge_index in range(len(graph.edges)) for fragment in range(num_fragments)}
    for qubit in range(n):
        model.addCons(quicksum(x[qubit, fragment] for fragment in range(num_fragments)) == 1)
    for fragment in range(num_fragments):
        load = quicksum(x[qubit, fragment] for qubit in range(n))
        model.addCons(load >= lower[fragment])
        model.addCons(load <= upper[fragment])
    for edge_index, edge in enumerate(graph.edges):
        for fragment in range(num_fragments):
            model.addCons(y[edge_index, fragment] <= x[edge.u, fragment])
            model.addCons(y[edge_index, fragment] <= x[edge.v, fragment])
            model.addCons(y[edge_index, fragment] >= x[edge.u, fragment] + x[edge.v, fragment] - 1)
        model.addCons(z[edge_index] + quicksum(y[edge_index, fragment] for fragment in range(num_fragments)) == 1)
    return x, z, y


def _add_exact_capacity_strengthening(
    model: Model,
    graph: InteractionGraph,
    x: dict[tuple[int, int], Any],
    z: dict[int, Any],
    num_fragments: int,
    lower: tuple[int, ...],
    upper: tuple[int, ...],
    *,
    cross_pair_strengthening: bool,
    metric_strengthening: bool,
    symmetry_breaking: bool,
) -> None:
    """Add valid fixed-size cardinality and equal-capacity symmetry constraints."""
    exact = lower == upper
    if symmetry_breaking and exact and len(set(lower)) == 1:
        model.addCons(x[0, 0] == 1)
    if not cross_pair_strengthening or not exact:
        return
    edge_by_pair = {(edge.u, edge.v): index for index, edge in enumerate(graph.edges)}
    all_pair_cuts: dict[tuple[int, int], Any] = {}
    for u in range(graph.num_qubits):
        for v in range(u + 1, graph.num_qubits):
            edge_index = edge_by_pair.get((u, v))
            if edge_index is not None:
                all_pair_cuts[u, v] = z[edge_index]
                continue
            pair_z = model.addVar(vtype="B", name=f"card_z_{u}_{v}")
            pair_y = [model.addVar(vtype="B", name=f"card_y_{u}_{v}_{fragment}") for fragment in range(num_fragments)]
            for fragment, local in enumerate(pair_y):
                model.addCons(local <= x[u, fragment])
                model.addCons(local <= x[v, fragment])
                model.addCons(local >= x[u, fragment] + x[v, fragment] - 1)
            model.addCons(pair_z + quicksum(pair_y) == 1)
            all_pair_cuts[u, v] = pair_z
    model.addCons(quicksum(all_pair_cuts.values()) == fixed_capacity_cross_pair_count(lower))
    if not metric_strengthening:
        return
    for u in range(graph.num_qubits):
        for v in range(u + 1, graph.num_qubits):
            for w in range(v + 1, graph.num_qubits):
                uv, uw, vw = all_pair_cuts[u, v], all_pair_cuts[u, w], all_pair_cuts[v, w]
                model.addCons(uv <= uw + vw)
                model.addCons(uw <= uv + vw)
                model.addCons(vw <= uv + uw)


def _capacities(
    num_qubits: int,
    num_fragments: int,
    lower_capacities: Sequence[int] | None,
    upper_capacities: Sequence[int] | None,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if num_qubits < 1:
        raise ValueError("graph must contain at least one qubit")
    if num_fragments < 1:
        raise ValueError("num_fragments must be positive")
    if lower_capacities is None:
        lower = (1,) * num_fragments
    else:
        lower = tuple(lower_capacities)
    if upper_capacities is None:
        upper = ((num_qubits + num_fragments - 1) // num_fragments,) * num_fragments
    else:
        upper = tuple(upper_capacities)
    if len(lower) != num_fragments or len(upper) != num_fragments:
        raise ValueError("capacity bounds must contain one value per fragment")
    if any(value < 0 for value in (*lower, *upper)) or any(lo > hi for lo, hi in zip(lower, upper, strict=True)):
        raise ValueError("capacity bounds must be nonnegative and satisfy lower <= upper")
    return lower, upper


def _result(
    graph: InteractionGraph,
    status: str,
    num_fragments: int,
    lower: tuple[int, ...],
    upper: tuple[int, ...],
    partition: tuple[int, ...] | None,
    certificate: Certificate | None,
    nodes: int,
    lp_iterations: int,
    runtime_s: float,
    bound_status: str,
    tolerance: float,
) -> KPartitionResult:
    if partition is None:
        return KPartitionResult(status, num_fragments, lower, upper, None, (), (), (), None, None, certificate,
                                nodes, lp_iterations, runtime_s, bound_status, tolerance)
    cut_edges = tuple((edge.u, edge.v) for edge in graph.edges if partition[edge.u] != partition[edge.v])
    cut_instruction_indices = tuple(
        instruction_index for edge in graph.edges if partition[edge.u] != partition[edge.v]
        for instruction_index in edge.instruction_indices
    )
    objective = graph_partition_objective(graph, partition)
    return KPartitionResult(
        status, num_fragments, lower, upper, partition,
        tuple(tuple(qubit for qubit, label in enumerate(partition) if label == fragment) for fragment in range(num_fragments)),
        cut_edges, cut_instruction_indices, objective, _safe_gamma(objective), certificate,
        nodes, lp_iterations, runtime_s, bound_status, tolerance,
    )


def _infeasible_result(num_fragments: int, lower: tuple[int, ...], upper: tuple[int, ...]) -> KPartitionResult:
    return KPartitionResult("infeasible", num_fragments, lower, upper, None, (), (), (), None, None, None,
                            0, 0, 0.0, "capacity infeasible", 0.0)


def _finite_bound(value: float) -> float | None:
    value = float(value)
    return value if isfinite(value) and abs(value) < 1e100 else None


def _safe_gamma(objective_log_cost: float) -> float | None:
    return None if objective_log_cost > log(sys.float_info.max) else exp(objective_log_cost)
