from math import isclose, log

from certicut.baselines.graph_heuristics import solve_graph_heuristic
from certicut.baselines.kahip import _to_csr, solve_kahip
from certicut.baselines.qiskit_cut_finder import find_gate_only_cuts, qiskit_track_b_record
from certicut.circuits.phase0 import make_six_qubit_toy_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition


def test_track_a_graph_heuristics_share_exact_balanced_objective() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    for variant in ("h2", "h3"):
        result = solve_graph_heuristic(graph, qmax=3, variant=variant)
        assert result.track == "A_exact_balanced"
        assert result.fragment_sizes == (3, 3)
        assert isclose(result.objective_log_cost or 0, log(81), abs_tol=1e-10)
        assert result.minimum_reached is None


def test_qiskit_gate_only_toy_cost_matches_cnot_independent_overhead() -> None:
    result = find_gate_only_cuts(make_six_qubit_toy_circuit(), qmax=3)
    assert result.track == "B_practical_qmax"
    assert result.cut_instruction_indices == (4, 5)
    assert result.sampling_overhead == 81.0
    assert isclose(result.objective_log_cost or 0, log(81), abs_tol=1e-10)
    assert result.minimum_reached is True


def test_qiskit_track_b_infinity_mode_and_overlap_metadata() -> None:
    record = qiskit_track_b_record(make_six_qubit_toy_circuit(), qmax=3, track_a_optimum_log=log(81))
    assert record["qiskit_max_gamma"] == "inf"
    assert record["qiskit_max_backjumps"] is None
    assert record["track_a_overlap"] is True
    assert isclose(record["objective_difference"], 0.0, abs_tol=1e-10)


def test_kahip_csr_uses_undirected_integer_cnot_multiplicities() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    vwgt, xadj, adjcwgt, adjncy = _to_csr(graph)
    assert vwgt == [1] * 6
    assert xadj[-1] == len(adjncy) == len(adjcwgt) == 12
    assert set(adjcwgt) == {1}


def test_kahip_strong_respects_track_a_balance_and_oracle_lower_bound() -> None:
    graph = build_interaction_graph(make_six_qubit_toy_circuit())
    result = solve_kahip(graph, seed=0, mode="strong")
    oracle = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
    assert result.status == "feasible"
    assert result.fragment_sizes == (3, 3)
    assert (oracle.objective_log_cost or 0) <= (result.objective_log_cost or 0) + 1e-10


def test_kahip_enforces_even_and_odd_exact_balance() -> None:
    from qiskit import QuantumCircuit
    for qubits, expected in ((8, (4, 4)), (9, (4, 5))):
        circuit = QuantumCircuit(qubits)
        for index in range(qubits - 1):
            circuit.cx(index, index + 1)
        result = solve_kahip(build_interaction_graph(circuit), seed=0, mode="strong")
        assert result.status == "feasible"
        assert tuple(sorted(result.fragment_sizes)) == expected
