"""Shared serializable baseline result schemas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, log
from typing import Any


@dataclass(frozen=True)
class BaselineResult:
    method: str
    track: str
    status: str
    runtime_s: float
    objective_log_cost: float | None
    sampling_overhead: float | None
    cut_instruction_indices: tuple[int, ...]
    fragment_sizes: tuple[int, ...]
    minimum_reached: bool | None
    notes: str
    partition: tuple[int, ...] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_overhead(log_cost: float | None) -> float | None:
    if log_cost is None or not isfinite(log_cost) or log_cost > log(float.fromhex("0x1.fffffffffffffp+1023")):
        return None
    return exp(log_cost)
