from math import isclose, log

from qiskit import QuantumCircuit

from certicut.optimization.pj_regret import exhaustive_pj_model_regret


def test_pj_regret_is_tie_safe_when_an_independent_optimum_is_joint_optimal() -> None:
    circuit = QuantumCircuit(4)
    circuit.cx(0, 1)
    circuit.cx(1, 2)
    circuit.cx(2, 3)
    circuit.cx(3, 0)

    result = exhaustive_pj_model_regret(circuit)

    assert result.independent_optimum_count > 1
    assert result.decision_regret_factor == 1.0
    assert not result.strict_model_reversal


def test_pj_regret_reports_known_strict_model_reversal() -> None:
    circuit = QuantumCircuit(6)
    circuit.iswap(5, 1)
    circuit.cx(0, 3)
    circuit.cx(4, 2)
    circuit.cx(3, 4)
    circuit.rzz(0.3, 2, 1)
    circuit.iswap(0, 5)
    circuit.rzz(0.7853981633974483, 0, 4)
    circuit.rzz(0.7853981633974483, 2, 5)
    circuit.iswap(3, 1)

    result = exhaustive_pj_model_regret(circuit)

    assert result.strict_model_reversal
    assert isclose(result.decision_delta_log_cost, log(1.9049616073489846), abs_tol=1e-10)
    assert isclose(result.decision_regret_factor, 1.9049616073489846, abs_tol=1e-10)
