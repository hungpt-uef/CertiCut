from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, iSwapGate

from certicut.optimization.pj_exact import solve_exact_pj_pattern_milp
from certicut.optimization.pj_lovasz_lp import solve_pj_lovasz_relaxation


def test_lovasz_lp_is_a_valid_lower_bound_for_exact_pj_oracle():
    circuit = QuantumCircuit(6)
    circuit.cx(0, 3)
    circuit.append(RZZGate(0.3), (1, 4))
    circuit.append(iSwapGate(), (2, 5))
    circuit.cx(0, 4)
    circuit.cx(1, 5)
    circuit.cx(2, 3)

    relaxation = solve_pj_lovasz_relaxation(circuit)
    exact = solve_exact_pj_pattern_milp(circuit)

    assert relaxation.status == exact.status == "optimal"
    assert relaxation.lower_bound_log <= (exact.objective_log_cost or 0.0) + 1e-9
    assert len(relaxation.cuts) > 0


def test_lovasz_lp_keeps_binary_zero_cut_solution_exact():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)

    relaxation = solve_pj_lovasz_relaxation(circuit)
    exact = solve_exact_pj_pattern_milp(circuit)

    assert abs(relaxation.lower_bound_log or 0.0) < 1e-12
    assert abs(exact.objective_log_cost or 0.0) < 1e-12
