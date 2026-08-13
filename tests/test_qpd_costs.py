from math import isclose, log, pi, sin, sqrt
import random

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import CCXGate, CSGate, CXGate, CZGate, DCXGate, RXXGate, RZZGate, iSwapGate

from certicut.costs.qpd import QPDCostUnboundParameter, QPDCostUnsupported, qpd_cost
from certicut.graph.interaction import build_interaction_graph, gate_level_partition_objective, graph_partition_objective
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import brute_force_exact_partition, solve_exact_partition


def test_qiskit_qpd_costs_match_known_reference_families() -> None:
    expected = ((CXGate(), 9.0), (CZGate(), 9.0), (CSGate(), 3 + 2 * sqrt(2)), (iSwapGate(), 49.0), (DCXGate(), 49.0))
    for gate, overhead in expected:
        assert isclose(qpd_cost(gate).overhead, overhead, rel_tol=0, abs_tol=1e-10)


def test_parameterized_qpd_costs_are_sensitive_to_gate_angle() -> None:
    for gate, angle, expected in (
        (RZZGate(0), 0, 1.0),
        (RZZGate(pi / 4), pi / 4, (1 + 2 * abs(sin(pi / 4))) ** 2),
        (RZZGate(pi / 2), pi / 2, 9.0),
        (RXXGate(pi / 4), pi / 4, (1 + 2 * abs(sin(pi / 4))) ** 2),
    ):
        assert isclose(qpd_cost(gate).overhead, expected, rel_tol=0, abs_tol=1e-10)


def test_qpd_costs_fail_fast_for_unbound_and_non_two_qubit_operations() -> None:
    try:
        qpd_cost(RZZGate(Parameter("theta")))
    except QPDCostUnboundParameter:
        pass
    else:
        raise AssertionError("unbound RZZ parameter was accepted")
    try:
        qpd_cost(CCXGate())
    except QPDCostUnsupported:
        pass
    else:
        raise AssertionError("three-qubit gate was accepted")


def test_mixed_gate_edge_aggregates_qpd_cost_and_matches_gate_level_objective() -> None:
    circuit = QuantumCircuit(2)
    circuit.cx(0, 1)
    circuit.append(RZZGate(pi / 4), [0, 1])
    circuit.append(iSwapGate(), [0, 1])
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    edge = graph.edges[0]
    expected = log(9) + log(3 + 2 * sqrt(2)) + log(49)
    assert isclose(edge.qpd_log_cost, expected, abs_tol=1e-10)
    assert isclose(graph_partition_objective(graph, (0, 1)), expected, abs_tol=1e-10)
    assert isclose(gate_level_partition_objective(circuit, (0, 1), cost_model="qiskit_qpd"), expected, abs_tol=1e-10)
    assert edge.gates[1].gate_params == (pi / 4,)
    assert edge.gates[1].qpd_source == "qiskit_qpd_0.10.0"


def test_sampling_aware_optimizer_prefers_lower_cost_at_same_cut_count() -> None:
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)
    circuit.append(CSGate(), [0, 1])
    circuit.append(CSGate(), [2, 3])
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    cx_plan = (0, 0, 1, 1)
    cs_plan = (0, 1, 0, 1)
    assert isclose(graph_partition_objective(graph, cx_plan), log(81), abs_tol=1e-10)
    assert isclose(graph_partition_objective(graph, cs_plan), log((3 + 2 * sqrt(2)) ** 2), abs_tol=1e-10)
    solution = solve_exact_partition(graph, num_fragments=2, qmax=2, exact_num_fragments=True)
    assert solution.partition == cs_plan


def test_sampling_aware_optimizer_can_prefer_more_cuts_with_lower_overhead() -> None:
    circuit = QuantumCircuit(4)
    circuit.append(iSwapGate(), [0, 2])
    circuit.append(iSwapGate(), [1, 3])
    for _ in range(3):
        circuit.cx(0, 1)
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    two_iswap = (0, 0, 1, 1)
    three_cx = (0, 1, 0, 1)
    assert isclose(graph_partition_objective(graph, two_iswap), log(49**2), abs_tol=1e-10)
    assert isclose(graph_partition_objective(graph, three_cx), log(9**3), abs_tol=1e-10)
    solution = solve_exact_partition(graph, num_fragments=2, qmax=2, exact_num_fragments=True)
    assert solution.partition == three_cx


def test_mixed_qpd_milp_and_bnb_match_brute_force_on_100_instances() -> None:
    generator = random.Random(20260811)
    for _ in range(100):
        n = generator.randint(4, 8)
        circuit = QuantumCircuit(n)
        for _ in range(generator.randint(1, 2 * n)):
            u, v = generator.sample(range(n), 2)
            operation = generator.choice(("cx", "cz", "cs", "rzz", "iswap"))
            if operation == "cx":
                circuit.cx(u, v)
            elif operation == "cz":
                circuit.cz(u, v)
            elif operation == "cs":
                circuit.append(CSGate(), [u, v])
            elif operation == "rzz":
                circuit.append(RZZGate(generator.choice((pi / 4, pi / 2))), [u, v])
            else:
                circuit.append(iSwapGate(), [u, v])
        graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
        qmax = (n + 1) // 2
        brute = brute_force_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        milp = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
        bnb = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant="h2")
        assert isclose(milp.objective_log_cost or 0, brute.objective_log_cost or 0, abs_tol=1e-10)
        assert bnb.certificate is not None and bnb.certificate.proven_optimal
        assert isclose(bnb.certificate.upper_bound_log, brute.objective_log_cost or 0, abs_tol=1e-10)
        limited = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, node_limit=0, lp_variant="b2s_root", warm_start_variant="h2")
        assert limited.certificate is not None
        assert limited.certificate.lower_bound_log <= (brute.objective_log_cost or 0) + 1e-10
        assert (brute.objective_log_cost or 0) <= limited.certificate.upper_bound_log + 1e-10
