"""Matched primal/dual SCIP audit formulations for core independent-QPD CertiCut."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from math import exp
from time import perf_counter
from typing import Literal, Sequence

from pyscipopt import Model, quicksum

from certicut.graph.interaction import InteractionGraph

CoreSCIPVariant = Literal["g0_basic", "g1_cardinality", "g2_b2s"]
SCIP_TOLERANCE_LABEL = "SCIP numerics/feastol"


@dataclass(frozen=True)
class SCIPCoreResult:
    variant: str
    status: str
    primal_bound: float | None
    dual_bound: float | None
    factor: float | None
    proven_optimal: bool
    nodes: int
    lp_iterations: int
    actual_runtime_s: float
    bound_status: str
    tolerance: float
    checkpoints: tuple["SCIPCheckpoint", ...] = ()

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SCIPCheckpoint:
    wall_time_limit_s: float
    upper_bound: float | None
    lower_bound: float | None
    factor: float | None
    status: str
    bound_status: str
    actual_runtime_s: float
    nodes: int
    lp_iterations: int


def solve_scip_core(
    graph: InteractionGraph,
    *,
    variant: CoreSCIPVariant,
    time_limit_s: float,
    incumbent_partition: Sequence[int] | None = None,
    checkpoint_times_s: Sequence[float] = (),
) -> SCIPCoreResult:
    """Solve deterministic K=2 weighted bisection; checkpoints use wall-time budgets.

    Bounds are valid up to ``SCIP_TOLERANCE_LABEL`` and reported with that label.
    """
    n = graph.num_qubits
    if n % 2:
        raise ValueError("core SCIP audit uses even exact-balanced sizes")
    if variant not in ("g0_basic", "g1_cardinality", "g2_b2s"):
        raise ValueError(f"unknown SCIP core variant '{variant}'")
    if time_limit_s < 0 or any(limit < 0 for limit in checkpoint_times_s):
        raise ValueError("SCIP time limits must be nonnegative")
    incumbent = _canonical_partition(n, incumbent_partition) if incumbent_partition is not None else None
    result = _solve_scip_core(graph, variant, time_limit_s, incumbent)
    checkpoints = tuple(_solve_scip_core(graph, variant, limit, incumbent) for limit in checkpoint_times_s)
    return SCIPCoreResult(
        result.variant, result.status, result.primal_bound, result.dual_bound,
        result.factor, result.proven_optimal, result.nodes, result.lp_iterations,
        result.actual_runtime_s, result.bound_status, result.tolerance,
        tuple(
            SCIPCheckpoint(
                limit, checkpoint.primal_bound, checkpoint.dual_bound, checkpoint.factor,
                checkpoint.status, checkpoint.bound_status, checkpoint.actual_runtime_s,
                checkpoint.nodes, checkpoint.lp_iterations,
            )
            for limit, checkpoint in zip(checkpoint_times_s, checkpoints, strict=True)
        ),
    )


def _solve_scip_core(
    graph: InteractionGraph,
    variant: CoreSCIPVariant,
    time_limit_s: float,
    incumbent: tuple[int, ...] | None,
) -> SCIPCoreResult:
    n = graph.num_qubits
    model = Model(f"certicut_{variant}")
    started = perf_counter()
    model.hideOutput(True)
    model.setRealParam("limits/time", time_limit_s)
    model.setIntParam("randomization/randomseedshift", 0)
    model.setIntParam("randomization/permutationseed", 0)
    z = [model.addVar(vtype="B", name=f"z_{q}") for q in range(n)]
    model.addCons(z[0] == 0)
    model.addCons(quicksum(z) == n // 2)
    pairs = tuple(combinations(range(n), 2)) if variant != "g0_basic" else tuple((edge.u, edge.v) for edge in graph.edges)
    x = {pair: model.addVar(vtype="B", name=f"x_{pair[0]}_{pair[1]}") for pair in pairs}
    for u, v in pairs:
        model.addCons(x[u, v] >= z[u] - z[v])
        model.addCons(x[u, v] >= z[v] - z[u])
        if variant != "g0_basic":
            model.addCons(x[u, v] <= z[u] + z[v])
            model.addCons(x[u, v] <= 2 - z[u] - z[v])
    if variant in ("g1_cardinality", "g2_b2s"):
        model.addCons(quicksum(x[pair] for pair in pairs) == (n // 2) * (n // 2))
    if variant == "g2_b2s":
        for i, j, k in combinations(range(n), 3):
            ij, ik, jk = x[i, j], x[i, k], x[j, k]
            model.addCons(ij <= ik + jk)
            model.addCons(ik <= ij + jk)
            model.addCons(jk <= ij + ik)
            model.addCons(ij + ik + jk <= 2)
    model.setObjective(quicksum(edge.qpd_log_cost * x[edge.u, edge.v] for edge in graph.edges), "minimize")
    if incumbent is not None:
        solution = model.createSol()
        for q, label in enumerate(incumbent):
            model.setSolVal(solution, z[q], label)
        for (u, v), variable in x.items():
            model.setSolVal(solution, variable, int(incumbent[u] != incumbent[v]))
        model.addSol(solution)
    model.optimize()
    status = str(model.getStatus())
    primal = model.getPrimalbound()
    dual = model.getDualbound()
    primal_value = float(primal) if abs(primal) < 1e100 else None
    dual_value = float(dual) if abs(dual) < 1e100 else None
    tolerance = float(model.getParam("numerics/feastol"))
    gap = primal_value - dual_value if primal_value is not None and dual_value is not None else None
    bound_status = SCIP_TOLERANCE_LABEL if gap is None or gap >= -tolerance else "SCIP bound inconsistency"
    factor = exp(max(0.0, gap)) if gap is not None and bound_status == SCIP_TOLERANCE_LABEL else None
    return SCIPCoreResult(
        variant, status, primal_value, dual_value, factor, status == "optimal",
        int(model.getNNodes()), int(model.getNLPIterations()), perf_counter() - started,
        bound_status, tolerance,
    )


def _canonical_partition(n: int, partition: Sequence[int]) -> tuple[int, ...]:
    if len(partition) != n or any(label not in (0, 1) for label in partition):
        raise ValueError("incumbent partition must contain one binary label per qubit")
    if partition.count(0) != n // 2 or partition.count(1) != n // 2:
        raise ValueError("incumbent partition must be exact-balanced")
    return tuple(int(label != partition[0]) for label in partition)
