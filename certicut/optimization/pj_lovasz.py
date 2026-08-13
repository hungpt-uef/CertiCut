"""Lovasz epigraph cuts for submodular parallel-joint layer costs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from certicut.optimization.parallel_joint import ParallelLayerGate, pj_layer_function


@dataclass(frozen=True)
class PJLovaszCut:
    """Globally valid eta >= sum_j marginal_j x_(permutation_j) epigraph cut."""

    instruction_order: tuple[int, ...]
    coefficients: tuple[float, ...]
    value_at_point: float


def make_pj_lovasz_cut(layer: Sequence[ParallelLayerGate], x_values: Sequence[float]) -> PJLovaszCut:
    """Greedy Lovasz separator for F(S)=f(sum_{g in S} c_g)."""
    if len(layer) != len(x_values):
        raise ValueError("layer and x_values must have equal length")
    ordered = sorted(zip(layer, x_values, strict=True), key=lambda item: (-item[1], item[0].instruction_index))
    total = 0.0
    previous = 0.0
    coeffs: list[float] = []
    value = 0.0
    for gate, x in ordered:
        total += gate.log_s
        current = pj_layer_function(total)
        marginal = current - previous
        coeffs.append(marginal)
        value += marginal * x
        previous = current
    return PJLovaszCut(tuple(g.instruction_index for g, _ in ordered), tuple(coeffs), value)


def pj_lovasz_binary_exact(layer: Sequence[ParallelLayerGate], x_values: Sequence[int]) -> bool:
    """Verify extension equality at a binary layer point."""
    cut = make_pj_lovasz_cut(layer, x_values)
    exact = pj_layer_function(sum(gate.log_s for gate, x in zip(layer, x_values, strict=True) if x))
    return abs(cut.value_at_point - exact) < 1e-10
