"""Directed-decimal intervals for log-domain QPD objective reporting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, localcontext
from math import exp
from typing import Iterable


@dataclass(frozen=True)
class LogInterval:
    lower: Decimal
    upper: Decimal
    precision: int

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def width(self) -> Decimal:
        return self.upper - self.lower


def log_overhead_interval(overheads: Iterable[float], *, precision: int = 80) -> LogInterval:
    """Enclose ``sum(log(rho))`` by directed decimal rounding.

    Inputs remain binary floats; this is a transparent reporting interval, not an
    exact certificate for an externally supplied irrational overhead constant.
    """
    values = tuple(overheads)
    if precision < 18:
        raise ValueError("precision must be at least 18 decimal digits")
    if any(value <= 0 for value in values):
        raise ValueError("overheads must be positive")
    with localcontext() as context:
        context.prec = precision
        context.rounding = ROUND_FLOOR
        lower = sum((Decimal(str(value)).ln() for value in values), Decimal(0))
        context.rounding = ROUND_CEILING
        upper = sum((Decimal(str(value)).ln() for value in values), Decimal(0))
        # Decimal.ln is correctly rounded but context behavior is implementation
        # specific; one final ulp outward makes the reported enclosure explicit.
        padding = Decimal(len(values) or 1).scaleb(1 - precision)
        lower -= padding
        upper += padding
    return LogInterval(lower, upper, precision)


def conservative_factor(upper_bound: LogInterval, lower_bound: LogInterval) -> float:
    """Return exp(UB.upper - LB.lower) for interval-safe gap reporting."""
    return exp(float(upper_bound.upper - lower_bound.lower))
