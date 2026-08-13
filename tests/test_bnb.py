from math import ceil, isclose, log
import random

from qiskit import QuantumCircuit

from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def test_bnb_completes_toy_with_exact_certificate_and_cut_plan() -> None:
    result = solve_certified_bnb(
        build_interaction_graph(make_six_qubit_toy_circuit()), qmax=3, exact_num_fragments=True
    )
    assert result.status == "optimal"
    assert result.partition == (0, 0, 0, 1, 1, 1)
    assert result.cut_edges == ((1, 4), (2, 3))
    assert result.cut_instruction_indices == (4, 5)
    assert result.certificate is not None
    assert isclose(result.certificate.lower_bound_log, log(81), abs_tol=1e-10)
    assert isclose(result.certificate.upper_bound_log, log(81), abs_tol=1e-10)
    assert result.certificate.proven_optimal


def test_bnb_matches_phase2_oracle_on_100_seeded_instances() -> None:
    generator = random.Random(20260810)
    for _ in range(100):
        num_qubits = generator.randint(4, 8)
        circuit = QuantumCircuit(num_qubits)
        for _ in range(generator.randint(1, 2 * num_qubits)):
            circuit.cx(*generator.sample(range(num_qubits), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(num_qubits / 2)
        result = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True)
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        assert result.status == "optimal"
        assert result.certificate is not None
        assert result.certificate.proven_optimal
        assert isclose(result.certificate.lower_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)
        assert isclose(result.certificate.upper_bound_log, oracle.objective_log_cost or 0, abs_tol=1e-10)


def test_node_limited_certificates_contain_phase2_optimum_and_remain_monotonic() -> None:
    generator = random.Random(20260810)
    for _ in range(30):
        num_qubits = generator.randint(5, 8)
        circuit = QuantumCircuit(num_qubits)
        for _ in range(2 * num_qubits):
            circuit.cx(*generator.sample(range(num_qubits), 2))
        graph = build_interaction_graph(circuit)
        qmax = ceil(num_qubits / 2)
        oracle = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        result = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, node_limit=1)
        assert result.status == "node_limit"
        assert result.certificate is not None
        assert result.certificate.lower_bound_log <= (oracle.objective_log_cost or 0) + 1e-10
        assert (oracle.objective_log_cost or 0) <= result.certificate.upper_bound_log + 1e-10
        lbs = [event.global_lb for event in result.timeline if event.global_lb is not None]
        ubs = [event.incumbent_ub for event in result.timeline if event.incumbent_ub is not None]
        assert lbs == sorted(lbs)
        assert ubs == sorted(ubs, reverse=True)


def test_zero_time_limit_preserves_root_in_global_lower_bound() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    oracle = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    result = solve_certified_bnb(graph, qmax=3, exact_num_fragments=True, time_limit_s=0)
    assert result.status == "time_limit"
    assert result.expanded_nodes == 0
    assert result.certificate is not None
    assert result.certificate.lower_bound_log <= (oracle.objective_log_cost or 0) + 1e-10
    assert (oracle.objective_log_cost or 0) <= result.certificate.upper_bound_log + 1e-10


def test_bnb_handles_infeasible_root() -> None:
    result = solve_certified_bnb(build_interaction_graph(QuantumCircuit(7)), qmax=3)
    assert result.status == "infeasible"
    assert result.certificate is None


def test_node_limited_runs_are_deterministic() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    first = solve_certified_bnb(graph, qmax=3, exact_num_fragments=True, node_limit=1)
    second = solve_certified_bnb(graph, qmax=3, exact_num_fragments=True, node_limit=1)
    assert first.status == second.status
    assert first.partition == second.partition
    assert first.certificate == second.certificate
    assert first.expanded_nodes == second.expanded_nodes
    assert [event.event for event in first.timeline] == [event.event for event in second.timeline]
    assert [event.global_lb for event in first.timeline] == [event.global_lb for event in second.timeline]
