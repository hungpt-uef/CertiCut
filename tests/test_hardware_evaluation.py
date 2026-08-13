from qiskit import QuantumCircuit

from certicut.hardware.evaluation import controlled_noise_model, evaluate_fragments, evaluate_noisy_z_observable


def test_fragment_evaluation_reports_routing_metrics() -> None:
    circuit = QuantumCircuit(4)
    circuit.cx(0, 3)
    circuit.cx(1, 2)
    result = evaluate_fragments(circuit, (0, 0, 0, 0), topology="line")
    assert result.total_two_qubit_gates >= 2
    assert result.maximum_depth >= 1
    assert result.negative_log_success_surrogate > 0


def test_controlled_noise_model_has_declared_local_quantum_errors() -> None:
    model = controlled_noise_model(two_qubit_error=0.01)
    assert "cx" in model.noise_instructions


def test_aer_noise_evaluation_returns_bounded_observable() -> None:
    circuit = QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0, 1)
    result = evaluate_noisy_z_observable(circuit, controlled_noise_model(two_qubit_error=0.01), shots=256)
    assert -1 <= result.noisy_z_expectation <= 1
    assert result.absolute_error >= 0
