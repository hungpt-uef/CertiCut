"""Unified JSONL record schema; non-applicable values remain null."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkRecord:
    instance_id: str
    method: str
    track: str
    status: str
    runtime_s: float | None
    objective_log: float | None
    sampling_overhead: float | None
    lb_log: float | None
    ub_log: float | None
    log_gap: float | None
    certified_factor: float | None
    bound_closed: bool | None
    proven_optimal: bool | None
    num_cuts: int | None
    fragment_sizes: tuple[int, ...] | None
    expanded_nodes: int | None
    root_time_s: float | None
    tree_time_s: float | None
    peak_memory_mb: float | None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
