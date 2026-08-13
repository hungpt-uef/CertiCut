from math import log

from qiskit import QuantumCircuit

from certicut.optimization.parallel_joint import parallel_layer_gates
from certicut.optimization.pj_lovasz import make_pj_lovasz_cut, pj_lovasz_binary_exact


def test_lovasz_two_cx_binary_vertices_are_exact():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)
    layer = parallel_layer_gates(circuit)

    assert pj_lovasz_binary_exact(layer, (0, 0))
    assert pj_lovasz_binary_exact(layer, (1, 0))
    assert pj_lovasz_binary_exact(layer, (0, 1))
    assert pj_lovasz_binary_exact(layer, (1, 1))

    cut = make_pj_lovasz_cut(layer, (1.0, 1.0))
    assert abs(sum(cut.coefficients) - log(49)) < 1e-10


def test_lovasz_marginals_decrease_for_concave_layer_cost():
    circuit = QuantumCircuit(6)
    circuit.cx(0, 3)
    circuit.cx(1, 4)
    circuit.cx(2, 5)
    cut = make_pj_lovasz_cut(parallel_layer_gates(circuit), (0.9, 0.8, 0.7))

    assert cut.coefficients[0] > cut.coefficients[1] > cut.coefficients[2]
