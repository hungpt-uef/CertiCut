from __future__ import annotations

import pytest
from qiskit import QuantumCircuit

from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.graph.interaction import build_interaction_graph
from scripts.run_e12_representation_placement_regret import (
    _near_balanced_capacities,
    _solve_cross_representation_mip,
    exhaustive_representation_regret,
    scip_representation_regret,
)


def _compare_exact_and_scip(family: str, n: int, k: int, time_limit_s: float = 60.0) -> None:
    paired = ingest_mqt_pair(family, n)
    circuit_a, audit_a = paired["cx_normalized"]
    circuit_b, _ = paired["native_qpd"]
    exact = exhaustive_representation_regret(
        circuit_a,
        circuit_b,
        K=k,
        family=family,
        n=n,
        source_fingerprint=audit_a.source_fingerprint,
    )
    scip = scip_representation_regret(
        circuit_a,
        circuit_b,
        K=k,
        family=family,
        n=n,
        source_fingerprint=audit_a.source_fingerprint,
        time_limit_s=time_limit_s,
        tau_opt=1e-9,
        feasibility_tolerance=1e-10,
    )
    assert scip.J_a_star == pytest.approx(exact.J_a_star, abs=1e-8)
    assert scip.J_b_star == pytest.approx(exact.J_b_star, abs=1e-8)
    assert scip.delta_a_to_b == pytest.approx(exact.delta_a_to_b, abs=1e-7)
    assert scip.delta_b_to_a == pytest.approx(exact.delta_b_to_a, abs=1e-7)
    assert scip.strict_reversal_a_to_b == exact.strict_reversal_a_to_b
    assert scip.strict_reversal_b_to_a == exact.strict_reversal_b_to_a


def test_near_balanced_capacity_policy_examples() -> None:
    assert _near_balanced_capacities(6, 3) == ((2, 2, 2), (2, 2, 2))
    assert _near_balanced_capacities(8, 3) == ((2, 2, 2), (3, 3, 3))
    assert _near_balanced_capacities(14, 3) == ((4, 4, 4), (5, 5, 5))


def test_small_scip_set_level_result_matches_exhaustive_reference() -> None:
    _compare_exact_and_scip("qpeexact", 6, 2, time_limit_s=30.0)


def test_numerically_stiff_grover_scip_result_matches_exhaustive_reference() -> None:
    # This case catches solver-tolerance choices that can return a suboptimal
    # Stage-1 incumbent and thereby alter the cross-representation conclusion.
    _compare_exact_and_scip("grover", 12, 2, time_limit_s=120.0)


def test_near_balanced_k3_scip_result_matches_exhaustive_reference() -> None:
    _compare_exact_and_scip("qaoa", 12, 3, time_limit_s=120.0)



def test_cross_stage_does_not_shortcut_when_only_primary_objective_is_zero() -> None:
    primary = QuantumCircuit(2)
    cross = QuantumCircuit(2)
    cross.cx(0, 1)
    graph_primary = build_interaction_graph(primary, cost_model="qiskit_qpd")
    graph_cross = build_interaction_graph(cross, cost_model="qiskit_qpd")
    value, partition, status = _solve_cross_representation_mip(
        graph_primary,
        graph_cross,
        J_primary_star=0.0,
        num_fragments=2,
        lower_capacities=(1, 1),
        upper_capacities=(1, 1),
        tau_opt=1e-9,
        feasibility_tolerance=1e-10,
        time_limit_s=30.0,
    )
    assert status == "optimal"
    assert partition is not None and len(partition) == 2
    assert value == pytest.approx(__import__("math").log(9.0))


def test_cross_stage_zero_objectives_build_complete_near_balanced_partition() -> None:
    empty = QuantumCircuit(4)
    graph = build_interaction_graph(empty, cost_model="qiskit_qpd")
    value, partition, status = _solve_cross_representation_mip(
        graph,
        graph,
        J_primary_star=0.0,
        num_fragments=3,
        lower_capacities=(1, 1, 1),
        upper_capacities=(2, 2, 2),
        tau_opt=1e-9,
        feasibility_tolerance=1e-10,
        time_limit_s=30.0,
    )
    assert status == "trivial"
    assert value == pytest.approx(0.0)
    assert partition is not None and len(partition) == 4
    loads = [partition.count(k) for k in range(3)]
    assert all(1 <= load <= 2 for load in loads)
