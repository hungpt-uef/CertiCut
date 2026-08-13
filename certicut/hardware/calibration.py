"""Validate frozen IBM calibration snapshots and convert them to QPU specifications."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from certicut.optimization.hypergraph_milp import QPUSpec


def _canonical_bytes(snapshot: Mapping[str, Any]) -> bytes:
    payload = dict(snapshot)
    payload.pop("sha256", None)
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8")


def qpu_spec_from_frozen_snapshot(
    snapshot: Mapping[str, Any] | Path,
    *,
    qpu_id: int = 0,
    capacity: int | None = None,
    preferred_gate_names: Sequence[str] = ("ecr", "cx", "cz"),
) -> QPUSpec:
    """Verify a frozen snapshot checksum and select the best two-qubit error per coupling pair."""
    if isinstance(snapshot, Path):
        snapshot = json.loads(snapshot.read_text(encoding="utf-8"))
    expected_hash = snapshot.get("sha256")
    if not isinstance(expected_hash, str):
        raise ValueError("calibration snapshot lacks sha256")
    actual_hash = hashlib.sha256(_canonical_bytes(snapshot)).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("calibration snapshot SHA-256 mismatch")
    if snapshot.get("schema_version") != 1:
        raise ValueError("unsupported calibration snapshot schema")

    sites = tuple(int(site) for site in snapshot["physical_qubits"])
    edges = tuple(tuple(int(site) for site in edge) for edge in snapshot["coupling_edges"])
    allowed = set(preferred_gate_names)
    errors: dict[tuple[int, int], float] = {}
    for key, value in snapshot.get("two_qubit_gate_errors", {}).items():
        operation, pair = key.split(":", 1)
        if operation not in allowed:
            continue
        first, second = (int(item) for item in pair.split(","))
        edge = tuple(sorted((first, second)))
        errors[edge] = min(errors.get(edge, float("inf")), float(value))
    readout = {int(site): float(error) for site, error in snapshot.get("readout_errors", {}).items()}
    actual_capacity = len(sites) if capacity is None else capacity
    if actual_capacity > len(sites):
        raise ValueError("requested capacity exceeds frozen physical site count")
    return QPUSpec(qpu_id, actual_capacity, edges, errors, readout, sites)


def connected_candidate_subgraph(spec: QPUSpec, *, candidate_count: int, seed_site: int | None = None) -> QPUSpec:
    """Prune a frozen backend to a deterministic connected physical-site candidate set.

    The snapshot stays unchanged. Pruning is an explicit solver candidate-site policy
    required to keep exact logical-to-physical MILP placement tractable.
    """
    if candidate_count < spec.capacity:
        raise ValueError("candidate_count must be at least the logical QPU capacity")
    sites = spec.sites()
    if candidate_count > len(sites):
        raise ValueError("candidate_count exceeds frozen backend size")
    adjacency = {site: set() for site in sites}
    for first, second in spec.coupling_edges:
        if first in adjacency and second in adjacency:
            adjacency[first].add(second)
            adjacency[second].add(first)
    root = min(sites) if seed_site is None else seed_site
    if root not in adjacency:
        raise ValueError("seed_site is absent from QPU physical sites")
    selected: list[int] = []
    queue = [root]
    seen = {root}
    while queue and len(selected) < candidate_count:
        site = queue.pop(0)
        selected.append(site)
        for neighbor in sorted(adjacency[site]):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    if len(selected) != candidate_count:
        raise ValueError("coupling graph component is smaller than requested candidate_count")
    selected_set = set(selected)
    edges = tuple(edge for edge in spec.coupling_edges if edge[0] in selected_set and edge[1] in selected_set)
    rates = {
        edge: value
        for edge, value in (spec.gate_error_rates or {}).items()
        if edge[0] in selected_set and edge[1] in selected_set
    }
    readout = {site: value for site, value in (spec.readout_error_rates or {}).items() if site in selected_set}
    return QPUSpec(spec.qpu_id, spec.capacity, edges, rates, readout, tuple(selected))
