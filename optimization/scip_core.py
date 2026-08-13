"""Matched primal/dual SCIP audit formulations for core independent-QPD CertiCut."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from math import exp
from typing import Literal

from pyscipopt import Model, quicksum

from certicut.graph.interaction import InteractionGraph


CoreSCIPVariant = Literal["g0_basic", "g1_cardinality", "g2_b2s"]


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

    def as_dict(self) -> dict:
        return asdict(self)


def solve_scip_core(
    graph: InteractionGraph,
    *,
    variant: CoreSCIPVariant,
    time_limit_s: float,
) -> SCIPCoreResult:
    """Solve the same exact-balanced K=2 objective with SCIP primal/dual logging."""
    n = graph.num_qubits
    if n % 2:
        raise ValueError("core SCIP audit uses even exact-balanced sizes")
    model = Model(f"certicut_{variant}")
    model.hideOutput(True)
    model.setRealParam("limits/time", time_limit_s)
    model.setIntParam("randomization/randomseedshift", 0)
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
    objective = quicksum(edge.qpd_log_cost * x[edge.u, edge.v] for edge in graph.edges)
    model.setObjective(objective, "minimize")
    model.optimize()
    status = str(model.getStatus())
    primal = model.getPrimalbound()
    dual = model.getDualbound()
    # SCIP uses infinities before a primal/dual bound exists.
    primal_value = float(primal) if abs(primal) < 1e100 else None
    dual_value = float(dual) if abs(dual) < 1e100 else None
    factor = exp(primal_value - dual_value) if primal_value is not None and dual_value is not None else None
    return SCIPCoreResult(
        variant,
        status,
        primal_value,
        dual_value,
        factor,
        status == "optimal",
        int(model.getNNodes()),
        int(model.getNLPIterations()),
        float(model.getSolvingTime()),
    )
