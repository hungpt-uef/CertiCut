"""Log-domain bound reports for certified anytime search.

The algebraic bound is exact only when its input bounds are exact.  Floating-
point LP backends therefore produce explicitly labelled solver-tolerance reports,
not independently verified numerical proofs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, log
import sys
from typing import Any


@dataclass(frozen=True)
class Certificate:
    lower_bound_log: float
    upper_bound_log: float
    additive_log_gap: float
    overhead_factor_bound: float | None
    bound_closed: bool
    proven_optimal: bool
    certificate_kind: str
    numerical_safety_margin_log: float
    conservative_lower_bound_log: float
    conservative_additive_log_gap: float
    conservative_overhead_factor_bound: float | None
    formal_numerical_proof: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_certificate(
    lower_bound_log: float,
    upper_bound_log: float,
    *,
    tolerance: float = 1e-9,
    numerical_safety_margin_log: float = 0.0,
    certificate_kind: str = "exact_arithmetic",
) -> Certificate:
    """Build a labelled bound report with an optional conservative LB margin.

    ``numerical_safety_margin_log`` is a declared one-sided allowance such that
    users may use ``LB_reported - margin`` when an external verifier establishes
    that allowance.  A solver feasibility tolerance alone does not establish it.
    """
    if not isfinite(lower_bound_log) or not isfinite(upper_bound_log):
        raise ValueError("certificate bounds must be finite")
    if tolerance < 0 or numerical_safety_margin_log < 0:
        raise ValueError("certificate tolerances must be nonnegative")
    if certificate_kind not in {"exact_arithmetic", "solver_tolerance", "verified_conservative"}:
        raise ValueError("unknown certificate kind")
    if lower_bound_log > upper_bound_log + tolerance:
        raise ValueError("lower bound exceeds upper bound")
    additive_gap = max(0.0, upper_bound_log - lower_bound_log)
    factor = None if additive_gap > log(sys.float_info.max) else exp(additive_gap)
    conservative_lb = lower_bound_log - numerical_safety_margin_log
    conservative_gap = max(0.0, upper_bound_log - conservative_lb)
    conservative_factor = (
        None if conservative_gap > log(sys.float_info.max) else exp(conservative_gap)
    )
    return Certificate(
        lower_bound_log=lower_bound_log,
        upper_bound_log=upper_bound_log,
        additive_log_gap=additive_gap,
        overhead_factor_bound=factor,
        bound_closed=additive_gap <= tolerance,
        proven_optimal=additive_gap <= tolerance,
        certificate_kind=certificate_kind,
        numerical_safety_margin_log=numerical_safety_margin_log,
        conservative_lower_bound_log=conservative_lb,
        conservative_additive_log_gap=conservative_gap,
        conservative_overhead_factor_bound=conservative_factor,
        formal_numerical_proof=certificate_kind in {"exact_arithmetic", "verified_conservative"},
    )
