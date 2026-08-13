import pytest
from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph, graph_partition_objective
from certicut.optimization.scip_core import SCIP_TOLERANCE_LABEL, solve_scip_core


def _graph():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)
    circuit.cx(0, 2)
    circuit.cx(1, 3)
    return build_interaction_graph(circuit)


def test_scip_checkpoints_accept_incumbent_and_match_wall_budgets():
    graph = _graph()
    supplied = (1, 1, 0, 0)
    result = solve_scip_core(
        graph, variant="g2_b2s", time_limit_s=1.0, incumbent_partition=supplied,
        checkpoint_times_s=(0.1, 0.2),
    )
    assert result.primal_bound is not None
    assert result.primal_bound <= graph_partition_objective(graph, supplied) + result.tolerance
    assert result.dual_bound is not None
    assert result.dual_bound <= result.primal_bound + result.tolerance
    assert result.factor is not None and result.factor >= 1.0
    assert result.bound_status == SCIP_TOLERANCE_LABEL
    assert [checkpoint.wall_time_limit_s for checkpoint in result.checkpoints] == [0.1, 0.2]
    assert all(checkpoint.bound_status == SCIP_TOLERANCE_LABEL for checkpoint in result.checkpoints)


def test_scip_checkpoints_reject_unbalanced_incumbent():
    with pytest.raises(ValueError, match="exact-balanced"):
        solve_scip_core(_graph(), variant="g0_basic", time_limit_s=1.0, incumbent_partition=(0, 0, 0, 1))
