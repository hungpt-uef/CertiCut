from math import isclose

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, iSwapGate

from certicut.optimization.pj_exact import brute_force_exact_pj, solve_exact_pj_pattern_milp


def test_pattern_milp_matches_brute_force_on_mixed_layered_instance():
    circuit = QuantumCircuit(6)
    circuit.cx(0, 3)
    circuit.append(RZZGate(0.3), (1, 4))
    circuit.append(iSwapGate(), (2, 5))
    circuit.cx(0, 1)
    circuit.cx(3, 4)

    milp_result = solve_exact_pj_pattern_milp(circuit)
    brute_result = brute_force_exact_pj(circuit)

    assert milp_result.status == brute_result.status == "optimal"
    assert isclose(milp_result.objective_log_cost or 0.0, brute_result.objective_log_cost or 0.0, abs_tol=1e-10)


def test_pattern_milp_matches_brute_force_for_parallel_cx_layer():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)

    result = solve_exact_pj_pattern_milp(circuit)

    reference = brute_force_exact_pj(circuit)
    assert result.status == reference.status == "optimal"
    assert isclose(result.objective_log_cost or 0.0, reference.objective_log_cost or 0.0, abs_tol=1e-10)
