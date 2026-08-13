"""Find the smallest CP0 cardinality/triangle synergy witness."""
from __future__ import annotations

from itertools import combinations, product
from random import Random

import numpy as np
from scipy.optimize import linprog
from types import SimpleNamespace

from certicut.optimization.core_root_lp import solve_core_root_lp
from certicut.optimization.exact import brute_force_exact_partition


def graph(n: int, weights: tuple[int, ...]) -> SimpleNamespace:
    return SimpleNamespace(
        num_qubits=n,
        edges=tuple(
            SimpleNamespace(u=u, v=v, qpd_log_cost=weight, instruction_indices=())
            for (u, v), weight in zip(combinations(range(n), 2), weights, strict=True)
            if weight
        ),
    )


def values(instance: SimpleNamespace) -> dict[str, float]:
    return {
        variant: solve_core_root_lp(instance, variant=variant).lower_bound
        for variant in ("b0", "cardinality", "triangles", "b2s")
    }


def is_witness(instance: SimpleNamespace) -> dict[str, float] | None:
    result = {"b0": solve_core_root_lp(instance, variant="b0").lower_bound}
    baseline = result["b0"]
    for variant in ("cardinality", "triangles"):
        result[variant] = solve_core_root_lp(instance, variant=variant).lower_bound
        if abs(result[variant] - baseline) >= 1e-9:
            return None
    result["b2s"] = solve_core_root_lp(instance, variant="b2s").lower_bound
    return result if result["b2s"] > baseline + 1e-9 else None


def search(n: int, maximum_weight: int) -> tuple[tuple[int, ...], dict[str, float]] | None:
    edge_count = n * (n - 1) // 2
    for weights in product(range(maximum_weight + 1), repeat=edge_count):
        result = is_witness(graph(n, weights))
        if result is not None:
            return weights, result
    return None


def random_search(n: int, maximum_weight: int, samples: int) -> tuple[tuple[int, ...], dict[str, float]] | None:
    rng = Random(20260812)
    edge_count = n * (n - 1) // 2
    for _ in range(samples):
        weights = tuple(rng.randrange(maximum_weight + 1) for _ in range(edge_count))
        result = is_witness(graph(n, weights))
        if result is not None:
            return weights, result
    return None


def minimize_support(n: int, weights: tuple[int, ...]) -> tuple[int, ...]:
    result = list(weights)
    for index, weight in enumerate(result):
        if not weight:
            continue
        candidate = result.copy()
        candidate[index] = 0
        if is_witness(graph(n, tuple(candidate))) is not None:
            result = candidate
    return tuple(result)


def b2s_dual(n: int, weights: tuple[int, ...]) -> None:
    """Print a HiGHS dual certificate for the full B2S system."""
    pairs = tuple(combinations(range(n), 2))
    pidx = {pair: n + index for index, pair in enumerate(pairs)}
    rows: list[tuple[str, list[float], float]] = []
    for u, v in pairs:
        for label, coefficients in (
            ("x-z_u+z_v>=0", ((u, 1), (v, -1), (pidx[u, v], -1))),
            ("x+z_u-z_v>=0", ((u, -1), (v, 1), (pidx[u, v], -1))),
            ("x-z_u-z_v<=0", ((u, -1), (v, -1), (pidx[u, v], 1))),
            ("x+z_u+z_v<=2", ((u, 1), (v, 1), (pidx[u, v], 1))),
        ):
            row = [0.0] * (n + len(pairs))
            for index, value in coefficients:
                row[index] = value
            rows.append((f"{u}{v}: {label}", row, 0.0 if ">=" in label else 2.0))
    for i, j, k in combinations(range(n), 3):
        ij, ik, jk = pidx[i, j], pidx[i, k], pidx[j, k]
        for label, coefficients, bound in (
            ("ij-ik-jk<=0", ((ij, 1), (ik, -1), (jk, -1)), 0),
            ("ik-ij-jk<=0", ((ik, 1), (ij, -1), (jk, -1)), 0),
            ("jk-ij-ik<=0", ((jk, 1), (ij, -1), (ik, -1)), 0),
            ("ij+ik+jk<=2", ((ij, 1), (ik, 1), (jk, 1)), 2),
        ):
            row = [0.0] * (n + len(pairs))
            for index, value in coefficients:
                row[index] = value
            rows.append((f"{i}{j}{k}: {label}", row, bound))
    objective = np.zeros(n + len(pairs))
    objective[n:] = weights
    equal = np.zeros((2, n + len(pairs)))
    equal[0, :n] = 1
    equal[1, n:] = 1
    raw = linprog(objective, A_ub=np.array([row for _, row, _ in rows]), b_ub=np.array([bound for _, _, bound in rows]), A_eq=equal, b_eq=(n / 2, (n // 2) ** 2), bounds=[(0, 0)] + [(0, 1)] * (n - 1 + len(pairs)), method="highs")
    assert raw.success
    print("dual equalities:", raw.eqlin.marginals)
    print("dual lower bounds:", raw.lower.marginals)
    print("dual upper bounds:", raw.upper.marginals)
    for (label, _, bound), multiplier in zip(rows, raw.ineqlin.marginals, strict=True):
        if abs(multiplier) > 1e-8:
            print(f"{multiplier:+g} * ({label}; rhs {bound:g})")


def main() -> None:
    # The smallest witness is the 6-vertex path 1-2-3-4 plus isolated 0,5.
    pairs6 = tuple(combinations(range(6), 2))
    path6 = tuple(int(edge in ((1, 2), (2, 3), (3, 4))) for edge in pairs6)
    instance6 = graph(6, path6)
    result6 = values(instance6)
    assert result6 == {"b0": 0.0, "cardinality": 0.0, "triangles": 0.0, "b2s": 1.0}
    optimum6 = brute_force_exact_partition(instance6, num_fragments=2, qmax=3, exact_num_fragments=True)
    assert optimum6.objective_log_cost == 1.0
    print("smallest witness pairs:", pairs6)
    print("smallest witness weights:", path6)
    print("smallest witness LP:", result6)
    print("smallest witness integral:", optimum6.objective_log_cost, optimum6.partition)
    b2s_dual(6, path6)
    return
    for n, maximum_weight, samples in ((2, 1, None), (4, 2, None), (6, 3, 10_000), (8, 1, 10_000)):
        witness = search(n, maximum_weight) if samples is None else random_search(n, maximum_weight, samples)
        print(f"n={n}, weights=0..{maximum_weight}: {witness}")
        if witness is not None:
            weights, result = witness
            weights = minimize_support(n, weights)
            result = values(graph(n, weights))
            instance = graph(n, weights)
            optimum = brute_force_exact_partition(
                instance, num_fragments=2, qmax=n // 2, exact_num_fragments=True
            )
            print("pairs:", tuple(combinations(range(n), 2)))
            print("weights:", weights)
            print("LP:", result)
            print("integral:", optimum.objective_log_cost, optimum.partition)
            return
    raise RuntimeError("No witness in configured exhaustive search.")


if __name__ == "__main__":
    main()
