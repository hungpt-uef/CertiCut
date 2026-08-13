"""Solver-agnostic root LP decomposition for B0, cardinality, triangle, and B2S."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from time import perf_counter
from typing import Literal

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from certicut.graph.interaction import InteractionGraph

RootVariant = Literal["b0", "cardinality", "triangles", "b2s"]


@dataclass(frozen=True)
class CoreRootLPResult:
    variant: str
    status: str
    lower_bound: float | None
    z_values: tuple[float, ...] | None
    x_values: dict[tuple[int, int], float] | None
    root_integral: bool
    separation_rounds: int
    active_triangles: tuple[tuple[int, int, int, int], ...]
    variable_count: int
    constraint_count: int
    lp_time_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def _violations(x: dict[tuple[int, int], float], n: int, tolerance: float):
    found = []
    for i, j, k in combinations(range(n), 3):
        ij, ik, jk = x[i, j], x[i, k], x[j, k]
        for kind, amount in enumerate((ij - ik - jk, ik - ij - jk, jk - ij - ik, ij + ik + jk - 2.0)):
            if amount > tolerance:
                found.append((amount, (i, j, k, kind)))
    return sorted(found, reverse=True)


def solve_core_root_lp(
    graph: InteractionGraph,
    *,
    variant: RootVariant,
    tolerance: float = 1e-9,
    max_rounds: int = 100,
) -> CoreRootLPResult:
    """Root LP with identical complete-pair variables and selected polyhedral families."""
    n = graph.num_qubits
    if n == 0 or n % 2:
        raise ValueError("root decomposition requires positive even size")
    if variant not in ("b0", "cardinality", "triangles", "b2s"):
        raise ValueError(f"unknown variant {variant}")
    pairs = tuple(combinations(range(n), 2))
    pidx = {pair: n + index for index, pair in enumerate(pairs)}
    triangle_enabled = variant in ("triangles", "b2s")
    cardinality_enabled = variant in ("cardinality", "b2s")
    active: list[tuple[int, int, int, int]] = []
    started = perf_counter()
    for round_id in range(max_rounds + 1):
        # balance, 4 XOR envelope rows per pair, optional cardinality, active triangles.
        rows = 1 + 4 * len(pairs) + (1 if cardinality_enabled else 0) + len(active)
        variables = n + len(pairs)
        matrix = lil_matrix((rows, variables), dtype=float)
        lower = np.full(rows, -np.inf)
        upper = np.full(rows, np.inf)
        row = 0
        for q in range(n):
            matrix[row, q] = 1.0
        lower[row] = upper[row] = n / 2
        row += 1
        for u, v in pairs:
            x = pidx[u, v]
            matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, -1.0, 1.0; lower[row] = 0.0; row += 1
            matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, 1.0, -1.0; lower[row] = 0.0; row += 1
            matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, -1.0, -1.0; upper[row] = 0.0; row += 1
            matrix[row, x], matrix[row, u], matrix[row, v] = 1.0, 1.0, 1.0; upper[row] = 2.0; row += 1
        if cardinality_enabled:
            for pair in pairs:
                matrix[row, pidx[pair]] = 1.0
            lower[row] = upper[row] = (n // 2) ** 2
            row += 1
        for i, j, k, kind in active:
            ij, ik, jk = pidx[i, j], pidx[i, k], pidx[j, k]
            if kind == 0:
                matrix[row, ij], matrix[row, ik], matrix[row, jk] = 1.0, -1.0, -1.0; upper[row] = 0.0
            elif kind == 1:
                matrix[row, ik], matrix[row, ij], matrix[row, jk] = 1.0, -1.0, -1.0; upper[row] = 0.0
            elif kind == 2:
                matrix[row, jk], matrix[row, ij], matrix[row, ik] = 1.0, -1.0, -1.0; upper[row] = 0.0
            else:
                matrix[row, ij], matrix[row, ik], matrix[row, jk] = 1.0, 1.0, 1.0; upper[row] = 2.0
            row += 1
        assert row == rows
        objective = np.zeros(variables)
        for edge in graph.edges:
            objective[pidx[edge.u, edge.v]] = edge.qpd_log_cost
        equal_rows = [0] + ([1 + 4 * len(pairs)] if cardinality_enabled else [])
        ge_rows = [r for r in range(rows) if r not in equal_rows and np.isfinite(lower[r])]
        le_rows = [r for r in range(rows) if r not in equal_rows and np.isfinite(upper[r])]
        a_ub = lil_matrix((len(ge_rows) + len(le_rows), variables), dtype=float)
        b_ub = np.empty(len(ge_rows) + len(le_rows))
        for out, source in enumerate(ge_rows):
            a_ub[out, :] = -matrix[source, :]; b_ub[out] = -lower[source]
        for out, source in enumerate(le_rows, start=len(ge_rows)):
            a_ub[out, :] = matrix[source, :]; b_ub[out] = upper[source]
        bounds = [(0.0, 1.0)] * variables
        bounds[0] = (0.0, 0.0)
        raw = linprog(
            objective,
            A_ub=a_ub.tocsr() if len(ge_rows) + len(le_rows) else None,
            b_ub=b_ub if len(ge_rows) + len(le_rows) else None,
            A_eq=matrix[equal_rows, :].tocsr(), b_eq=lower[equal_rows],
            bounds=bounds, method="highs",
        )
        if raw.status == 2:
            return CoreRootLPResult(variant, "infeasible", None, None, None, False, round_id, tuple(active), variables, rows, perf_counter() - started)
        if raw.status != 0 or raw.x is None:
            raise RuntimeError(f"root LP failed: {raw.status}: {raw.message}")
        z = tuple(float(raw.x[q]) for q in range(n))
        x = {pair: float(raw.x[pidx[pair]]) for pair in pairs}
        if not triangle_enabled:
            return CoreRootLPResult(variant, "optimal", float(raw.fun), z, x, all(abs(v-round(v)) < tolerance for v in z), round_id, tuple(active), variables, rows, perf_counter() - started)
        additions = [cut for _, cut in _violations(x, n, tolerance) if cut not in set(active)]
        if not additions:
            return CoreRootLPResult(variant, "optimal", float(raw.fun), z, x, all(abs(v-round(v)) < tolerance for v in z), round_id, tuple(active), variables, rows, perf_counter() - started)
        active.extend(additions)
    raise RuntimeError("root triangle separation exceeded max_rounds")
