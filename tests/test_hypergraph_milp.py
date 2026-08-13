"""Unit and integration tests for Hypergraph SVD Schmidt rank & Max-K-Cut Unbalanced MILP."""

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, CZGate, iSwapGate, RZZGate

from certicut.graph.hypergraph import build_hypergraph, compute_block_schmidt_rank
from certicut.hardware.calibration import connected_candidate_subgraph, qpu_spec_from_frozen_snapshot
from certicut.optimization.hypergraph_milp import QPUSpec, estimate_swap_count, solve_max_k_cut_unbalanced


def test_block_schmidt_rank_single_gates():
    # Test Schmidt rank calculation for standard gates
    qc_cx = QuantumCircuit(2)
    qc_cx.cx(0, 1)
    rank_cx = compute_block_schmidt_rank(qc_cx, [0], [0, 1])
    assert rank_cx == 2

    qc_iswap = QuantumCircuit(2)
    qc_iswap.iswap(0, 1)
    rank_iswap = compute_block_schmidt_rank(qc_iswap, [0], [0, 1])
    assert rank_iswap == 4


def test_hypergraph_construction():
    qc = QuantumCircuit(4)
    qc.cx(0, 1)
    qc.cx(0, 1)
    qc.rzz(np.pi / 4, 1, 2)
    qc.cz(2, 3)

    hg = build_hypergraph(qc)
    assert hg.num_qubits == 4
    assert len(hg.hyperedges) == 3

    # Check hyperedges
    e_01 = next(e for e in hg.hyperedges if e.qubits == (0, 1))
    assert len(e_01.gate_indices) == 2
    assert e_01.schmidt_rank >= 1


def test_temporal_spatial_blocks_create_true_joint_hyperedge():
    qc = QuantumCircuit(3)
    qc.iswap(0, 1)
    qc.iswap(1, 2)

    hg = build_hypergraph(qc, block_strategy="temporal_spatial", depth_window=2, max_block_qubits=3)

    assert len(hg.hyperedges) == 1
    edge = hg.hyperedges[0]
    assert edge.qubits == (0, 1, 2)
    assert edge.schmidt_rank > 2
    assert len(edge.partition_log_ranks) == 3


def test_rank_one_block_has_exact_zero_weight():
    qc = QuantumCircuit(2)
    qc.rzz(0.0, 0, 1)

    edge = build_hypergraph(qc).hyperedges[0]

    assert edge.schmidt_rank == 1
    assert edge.weight == 0.0


def test_max_k_cut_unbalanced_basic():
    qc = QuantumCircuit(6)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(3, 4)
    qc.cx(4, 5)

    hg = build_hypergraph(qc)
    sol = solve_max_k_cut_unbalanced(
        hg,
        num_qpus=2,
        qpu_capacities=[3, 3],
        alpha=1.0,
        beta=0.0,
        gamma=0.0,
    )

    assert sol.status == "optimal"
    assert sol.num_qpus == 2
    assert len(sol.partition) == 6
    assert len(sol.fragments[0]) <= 3
    assert len(sol.fragments[1]) <= 3


def test_hardware_noise_integration():
    qc = QuantumCircuit(6)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    qc.cx(3, 4)
    qc.cx(4, 5)

    hg = build_hypergraph(qc)

    # Define 2 QPUs with Heavy-Hex style line/grid topology specs and readout errors
    qpu0 = QPUSpec(
        qpu_id=0,
        capacity=4,
        coupling_edges=((0, 1), (1, 2), (2, 3)),
        readout_error_rates={0: 0.01, 1: 0.02, 2: 0.01, 3: 0.03},
    )
    qpu1 = QPUSpec(
        qpu_id=1,
        capacity=4,
        coupling_edges=((0, 1), (1, 2), (2, 3)),
        readout_error_rates={0: 0.01, 1: 0.01, 2: 0.02, 3: 0.02},
    )

    sol = solve_max_k_cut_unbalanced(
        hg,
        num_qpus=2,
        qpu_specs=[qpu0, qpu1],
        alpha=1.0,
        beta=0.5,
        gamma=0.5,
    )

    assert sol.status == "optimal"
    assert sol.objective_value is not None
    assert sol.cut_cost is not None
    assert sol.swap_cost_estimate is not None
    assert sol.error_cost is not None


def test_solver_integrates_placement_routing_and_gate_error_costs():
    qc = QuantumCircuit(3)
    qc.cx(0, 1)
    qc.cx(1, 2)
    hg = build_hypergraph(qc, block_strategy="temporal_spatial")
    qpu0 = QPUSpec(
        qpu_id=0,
        capacity=3,
        coupling_edges=((0, 1), (1, 2)),
        gate_error_rates={(0, 1): 0.01, (1, 2): 0.02},
        readout_error_rates={0: 0.001, 1: 0.002, 2: 0.003},
        physical_qubits=(0, 1, 2),
    )

    sol = solve_max_k_cut_unbalanced(
        hg,
        num_qpus=1,
        qpu_specs=[qpu0],
        alpha=0.0,
        beta=1.0,
        gamma=1.0,
        delta=1.0,
    )

    assert sol.status == "optimal"
    assert len({placement for placement in sol.physical_placements}) == 3
    assert sol.routing_cost == 0.0
    assert sol.gate_error_cost > 0.0
    assert sol.objective_value == pytest.approx(
        sol.readout_error_cost + sol.gate_error_cost, abs=1e-9
    )


def test_gate_error_weight_changes_solver_decision():
    qc = QuantumCircuit(4)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)
    hg = build_hypergraph(qc, block_strategy="temporal_spatial")
    specs = [
        QPUSpec(0, 2, ((0, 1),), {(0, 1): 0.5}, {0: 0.0, 1: 0.0}, (0, 1)),
        QPUSpec(1, 2, ((0, 1),), {(0, 1): 0.001}, {0: 0.0, 1: 0.0}, (0, 1)),
    ]

    cut_only = solve_max_k_cut_unbalanced(
        hg, num_qpus=2, qpu_specs=specs, alpha=0.01, beta=0.0, gamma=0.0, delta=0.0,
        require_nonempty_qpus=True,
    )
    error_aware = solve_max_k_cut_unbalanced(
        hg, num_qpus=2, qpu_specs=specs, alpha=0.01, beta=0.0, gamma=0.0, delta=10.0,
        require_nonempty_qpus=True,
    )

    assert cut_only.partition != error_aware.partition
    assert error_aware.gate_error_cost < cut_only.gate_error_cost


def test_routing_weight_changes_physical_placement():
    qc = QuantumCircuit(4)
    qc.cx(0, 2)
    qc.cx(1, 2)
    qc.cx(2, 3)
    hg = build_hypergraph(qc, block_strategy="temporal_spatial")
    spec = QPUSpec(
        0, 4, ((0, 1), (1, 2), (2, 3)),
        {(0, 1): 0.01, (1, 2): 0.01, (2, 3): 0.01},
        {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}, (0, 1, 2, 3),
    )

    no_routing = solve_max_k_cut_unbalanced(
        hg, num_qpus=1, qpu_specs=[spec], alpha=0.0, beta=0.0, gamma=0.0, delta=0.0
    )
    routing_aware = solve_max_k_cut_unbalanced(
        hg, num_qpus=1, qpu_specs=[spec], alpha=0.0, beta=1.0, gamma=0.0, delta=0.0
    )

    assert no_routing.physical_placements != routing_aware.physical_placements
    assert routing_aware.routing_cost < no_routing.routing_cost


def test_frozen_calibration_snapshot_checksum_validation():
    import hashlib
    import json

    snapshot = {
        "schema_version": 1,
        "fetched_at_utc": "2026-08-11T00:00:00+00:00",
        "backend_name": "fixture_backend",
        "backend_version": "test",
        "num_qubits": 2,
        "physical_qubits": (0, 1),
        "coupling_edges": ((0, 1),),
        "readout_errors": {"0": 0.01, "1": 0.02},
        "two_qubit_gate_errors": {"cx:0,1": 0.03},
        "source": "fixture",
    }
    snapshot["sha256"] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, indent=2).encode()).hexdigest()

    spec = qpu_spec_from_frozen_snapshot(snapshot)
    assert spec.capacity == 2
    assert spec.gate_error_rates[(0, 1)] == 0.03

    snapshot["readout_errors"]["0"] = 0.9
    with pytest.raises(ValueError, match="SHA-256"):
        qpu_spec_from_frozen_snapshot(snapshot)


def test_candidate_subgraph_preserves_connected_calibrated_sites():
    spec = QPUSpec(
        0, 3, ((0, 1), (1, 2), (2, 3)), {(0, 1): 0.01, (1, 2): 0.02, (2, 3): 0.03},
        {0: 0.01, 1: 0.02, 2: 0.03, 3: 0.04}, (0, 1, 2, 3),
    )
    candidate = connected_candidate_subgraph(spec, candidate_count=3)

    assert candidate.sites() == (0, 1, 2)
    assert candidate.coupling_edges == ((0, 1), (1, 2))
    assert candidate.gate_error_rates[(1, 2)] == 0.02
