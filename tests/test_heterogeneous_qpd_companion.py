from math import exp, isclose

from certicut.circuits.benchmarks import make_heterogeneous_qpd_circuit
from certicut.graph.interaction import build_interaction_graph, graph_partition_objective, valid_two_fragment_partitions
from certicut.optimization.bnb import solve_certified_bnb


COUNT_OVERHEADS = {"cx": exp(1), "cz": exp(1), "iswap": exp(1), "rzz": exp(1)}


def test_heterogeneous_qpd_generators_cover_validated_palette_and_match_count_objective() -> None:
    families = ("random_matching", "ring_even_odd", "community_matching", "dense_shuffled", "weighted_repeat")
    for family in families:
        circuit = make_heterogeneous_qpd_circuit(family, 14 if family == "community_matching" else 12, 7)
        names = {instruction.operation.name for instruction in circuit.data}
        assert names == {"cx", "cz", "iswap", "rzz"}
        assert {float(instruction.operation.params[0]) for instruction in circuit.data if instruction.operation.name == "rzz"} == {0.39269908169872414, 0.7853981633974483, 1.5707963267948966}
        qpd_graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
        count_graph = build_interaction_graph(circuit, cost_model="legacy_cx", qpd_overheads=COUNT_OVERHEADS)
        for partition in valid_two_fragment_partitions(circuit.num_qubits, circuit.num_qubits // 2):
            count = sum(1 for instruction in circuit.data if instruction.operation.num_qubits == 2 and partition[circuit.find_bit(instruction.qubits[0]).index] != partition[circuit.find_bit(instruction.qubits[1]).index])
            assert isclose(graph_partition_objective(count_graph, partition), count, abs_tol=1e-10)
        result = solve_certified_bnb(qpd_graph, qmax=circuit.num_qubits // 2, exact_num_fragments=True, node_limit=0, lp_variant="b2s_root", warm_start_variant="h2")
        assert result.certificate is not None
