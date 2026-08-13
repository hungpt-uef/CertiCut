from math import isclose, log

from qiskit import QuantumCircuit

from certicut.optimization.parallel_joint import (
    evaluate_parallel_joint_partition,
    exact_balanced_partitions,
    pj_layer_function,
)


def test_parallel_joint_layer_formula_matches_two_parallel_cx_theorem():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.cx(1, 3)

    evaluation = evaluate_parallel_joint_partition(circuit, (0, 0, 1, 1))

    assert isclose(evaluation.parallel_joint_log_cost, log(49), abs_tol=1e-12)
    assert isclose(evaluation.independent_log_cost, log(81), abs_tol=1e-12)
    assert isclose(evaluation.parallel_joint_overhead, 49.0, abs_tol=1e-12)


def test_parallel_joint_keeps_two_cx_in_separate_layers_independent():
    circuit = QuantumCircuit(4)
    circuit.cx(0, 2)
    circuit.x(1)  # Separates the next cross gate into a later dependency layer.
    circuit.cx(1, 3)

    evaluation = evaluate_parallel_joint_partition(circuit, (0, 0, 1, 1))

    assert isclose(evaluation.parallel_joint_log_cost, log(81), abs_tol=1e-12)
    assert len(evaluation.crossed_by_layer) == 2


def test_parallel_joint_layer_cost_is_increasing_concave():
    values = (0.0, 0.5, 1.0)
    assert pj_layer_function(values[1]) > pj_layer_function(values[0])
    slope_left = pj_layer_function(values[1]) - pj_layer_function(values[0])
    slope_right = pj_layer_function(values[2]) - pj_layer_function(values[1])
    assert slope_right < slope_left


def test_exact_balanced_partitions_fix_global_label_symmetry():
    partitions = exact_balanced_partitions(6)
    assert len(partitions) == 10
    assert all(partition[0] == 0 and sum(partition) == 3 for partition in partitions)
