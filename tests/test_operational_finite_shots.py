from dataclasses import replace
from math import pi

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate

from certicut.graph.interaction import build_interaction_graph, graph_partition_objective
from certicut.optimization.exact import solve_exact_partition
from certicut.qiskit_bridge.operational import validate_finite_shot_comparison


def test_finite_shot_comparison_uses_fixed_deterministic_budgets() -> None:
    circuit = QuantumCircuit(6)
    for qubit in range(6):
        circuit.h(qubit)
        circuit.append(RZZGate(pi / 4), [qubit, (qubit + 1) % 6])
    graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
    optimal = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    partition = (0, 0, 0, 1, 1, 1)
    alternative = replace(
        optimal,
        partition=partition,
        fragments=((0, 1, 2), (3, 4, 5)),
        cut_edges=tuple((edge.u, edge.v) for edge in graph.edges if partition[edge.u] != partition[edge.v]),
        cut_instruction_indices=tuple(
            index
            for edge in graph.edges
            if partition[edge.u] != partition[edge.v]
            for index in edge.instruction_indices
        ),
        objective_log_cost=graph_partition_objective(graph, partition),
    )
    kwargs = dict(
        total_shots_per_seed=200,
        qpd_samples_per_seed=4,
        seeds=(11, 22),
        observables=("ZZZZZZ", "XIIIII"),
    )
    result = validate_finite_shot_comparison(circuit, graph, (optimal, alternative), **kwargs)
    assert result == validate_finite_shot_comparison(circuit, graph, (optimal, alternative), **kwargs)
    assert all(plan.trial_shot_totals == (200, 200) for plan in result.plans)
    assert all(len(observable.estimator_distribution) == 2 for plan in result.plans for observable in plan.observables)
    assert all(observable.rmse >= abs(observable.bias) for plan in result.plans for observable in plan.observables)
