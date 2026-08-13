from math import exp, isclose, pi

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition
from certicut.qiskit_bridge.operational import validate_exact_reconstruction


def test_certicut_native_qpd_plan_reconstructs_exact_observable_and_overhead() -> None:
    circuit = QuantumCircuit(6)
    for qubit in range(6):
        circuit.h(qubit)
        circuit.rx(pi / 6, qubit)
    for qubit in range(6):
        circuit.append(RZZGate(pi / 4), [qubit, (qubit + 1) % 6])
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    solution = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    validation = validate_exact_reconstruction(circuit, graph, solution)
    assert isclose(validation.optimizer_log_cost, validation.qpd_log_overhead, abs_tol=1e-10)
    assert isclose(validation.qpd_overhead or 0, exp(validation.optimizer_log_cost), abs_tol=1e-10)
    assert validation.absolute_error < 1e-10
