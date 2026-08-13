from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, iSwapGate

from certicut.optimization.pj_bnb import solve_certified_pj_bnb
from certicut.optimization.pj_exact import solve_exact_pj_pattern_milp


def _mixed_instance() -> QuantumCircuit:
    circuit = QuantumCircuit(6)
    circuit.cx(0, 3)
    circuit.append(RZZGate(0.3), (1, 4))
    circuit.append(iSwapGate(), (2, 5))
    circuit.cx(0, 4)
    circuit.cx(1, 5)
    circuit.cx(2, 3)
    return circuit


def test_certified_pj_bnb_matches_exact_pattern_oracle():
    circuit = _mixed_instance()
    exact = solve_exact_pj_pattern_milp(circuit)
    result = solve_certified_pj_bnb(circuit)

    assert result.status == "optimal"
    assert result.certificate.proven_optimal
    assert abs(result.certificate.upper_bound_log - (exact.objective_log_cost or 0.0)) < 1e-9
    assert result.certificate.lower_bound_log <= (exact.objective_log_cost or 0.0) + 1e-9


def test_node_limited_pj_bnb_certificate_contains_exact_oracle():
    circuit = _mixed_instance()
    exact = solve_exact_pj_pattern_milp(circuit)
    result = solve_certified_pj_bnb(circuit, node_limit=0)

    assert result.status == "node_limit"
    assert result.certificate.lower_bound_log <= (exact.objective_log_cost or 0.0) + 1e-9
    assert (exact.objective_log_cost or 0.0) <= result.certificate.upper_bound_log + 1e-9


def test_pj_timeline_bounds_are_monotone_at_safe_checkpoints():
    result = solve_certified_pj_bnb(_mixed_instance())
    lower = [event.global_lb for event in result.timeline]
    upper = [event.incumbent_ub for event in result.timeline]

    assert all(next_value >= value - 1e-9 for value, next_value in zip(lower, lower[1:]))
    assert all(next_value <= value + 1e-9 for value, next_value in zip(upper, upper[1:]))


def test_pj_bnb_handles_multiple_layers_sharing_one_pair_variable():
    circuit = QuantumCircuit(6)
    circuit.cx(0, 3)
    circuit.cx(1, 4)
    circuit.cx(0, 3)  # Same logical pair in a later layer.
    circuit.append(RZZGate(0.3), (2, 5))
    exact = solve_exact_pj_pattern_milp(circuit)
    result = solve_certified_pj_bnb(circuit)

    assert result.certificate.proven_optimal
    assert abs(result.certificate.upper_bound_log - (exact.objective_log_cost or 0.0)) < 1e-9


def test_incomplete_pj_separation_remains_certificate_safe():
    circuit = _mixed_instance()
    exact = solve_exact_pj_pattern_milp(circuit)
    # A zero round limit deliberately returns a restricted, potentially weak LP.
    result = solve_certified_pj_bnb(circuit, node_limit=0, separation_round_limit=0)

    assert result.certificate.lower_bound_log <= (exact.objective_log_cost or 0.0) + 1e-9
    assert (exact.objective_log_cost or 0.0) <= result.certificate.upper_bound_log + 1e-9
