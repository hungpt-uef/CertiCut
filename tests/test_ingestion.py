from math import pi

from certicut.circuits.ingestion import V1_BASIS_GATES, ingest_mqt_benchmark, ingest_mqt_pair


def test_mqt_ingestion_is_deterministic_and_cx_only() -> None:
    first, audit = ingest_mqt_benchmark("qft", 8)
    second, repeated = ingest_mqt_benchmark("qft", 8)
    assert audit.audit_passed
    assert audit.two_qubit_gate_types == ("cx",)
    assert audit.unsupported_two_qubit_gates == ()
    assert audit.transpile_basis == V1_BASIS_GATES
    assert audit.circuit_fingerprint == repeated.circuit_fingerprint
    assert first.count_ops() == second.count_ops()


def test_mqt_algorithmic_families_ingest_under_v1_cx_audit() -> None:
    for family in ("qft", "qaoa", "ghz", "grover", "bv", "vqe_real_amp"):
        _, audit = ingest_mqt_benchmark(family, 8)
        assert audit.audit_passed
        assert audit.cx_count >= 0


def test_native_qpd_pair_preserves_source_and_qaoa_rzz_parameters() -> None:
    paired = ingest_mqt_pair("qaoa", 8)
    _, cx = paired["cx_normalized"]
    native_circuit, native = paired["native_qpd"]
    assert cx.source_fingerprint == native.source_fingerprint
    assert cx.two_qubit_gate_types == ("cx",)
    assert native.two_qubit_gate_types == ("rzz",)
    assert native.audit_passed
    assert all(instruction.operation.num_qubits <= 2 for instruction in native_circuit.data)
    assert any(abs(float(instruction.operation.params[0])) > 0 for instruction in native_circuit.data if instruction.operation.name == "rzz")


def test_native_vqe_control_matches_cx_two_qubit_representation() -> None:
    paired = ingest_mqt_pair("vqe_real_amp", 8)
    _, cx = paired["cx_normalized"]
    _, native = paired["native_qpd"]
    assert cx.cx_count == native.cx_count
    assert native.two_qubit_gate_types == ("cx",)
