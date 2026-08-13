"""Extract deterministic anytime snapshots from one B&B trajectory."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from certicut.optimization.bnb import BnBResult


@dataclass(frozen=True)
class CheckpointRecord:
    node_limit: int
    expanded_nodes: int
    elapsed_s: float
    lb_log: float
    ub_log: float
    log_gap: float
    certified_factor: float | None
    bound_closed: bool
    proven_optimal: bool
    frontier_size: int

    def as_dict(self):
        return asdict(self)


def extract_checkpoints(result: BnBResult, limits: tuple[int, ...]) -> tuple[CheckpointRecord, ...]:
    """Forward-fill named budgets from a single deterministic safe-checkpoint trajectory."""
    if result.certificate is None or not result.timeline:
        return ()
    events = sorted(result.timeline, key=lambda event: event.expanded_nodes)
    snapshots = []
    for limit in limits:
        eligible = [event for event in events if event.expanded_nodes <= limit]
        event = eligible[-1] if eligible else events[0]
        snapshots.append(CheckpointRecord(
            node_limit=limit,
            expanded_nodes=event.expanded_nodes,
            elapsed_s=event.elapsed_s,
            lb_log=event.global_lb if event.global_lb is not None else result.certificate.lower_bound_log,
            ub_log=event.incumbent_ub if event.incumbent_ub is not None else result.certificate.upper_bound_log,
            log_gap=event.additive_log_gap if event.additive_log_gap is not None else result.certificate.additive_log_gap,
            certified_factor=event.overhead_factor_bound,
            bound_closed=(event.additive_log_gap or 0.0) <= 1e-9,
            proven_optimal=(event.additive_log_gap or 0.0) <= 1e-9 and event.open_nodes == 0,
            frontier_size=event.open_nodes,
        ))
    return tuple(snapshots)
