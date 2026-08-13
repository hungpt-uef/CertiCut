# CertiCut Phase 6.3 Real Quantum Circuit Ingestion Report

Ngày: 11/08/2026

## Trạng thái

PASS. Real algorithmic circuits from MQT Bench are reproducibly transformed into audited logical CX-only representations before entering Track A optimization.

## Protocol

Source:

```text
MQT Bench == 2.2.2
```

Logical transpilation:

```text
basis_gates = [rz, sx, x, cx]
coupling_map = None
optimization_level = 1
seed_transpiler = 0
```

No hardware coupling map, layout, or routing target is specified. This benchmark optimizes the selected logical transpiled CNOT representation, not a hardware-routed implementation or the abstract high-level algorithm.

Measurements and barriers are removed explicitly before transpilation. Every source-qubit reference is remapped by index into a fresh circuit; this avoids cross-register aliasing from MQT-provided circuits.

## Audit Rule

```text
audit_passed iff every transpiled two-qubit instruction is cx
```

Any unsupported two-qubit gate is surfaced as an audit failure. No gate receives an invented CNOT/QPD cost.

Audit metadata records source/family/size, transpile configuration, original/transpiled operation and depth counts, all two-qubit types, final CX count, unsupported gate types, and a SHA-256 circuit fingerprint.

`bound_closed` is now exposed alongside strict `proven_optimal`:

```text
bound_closed = UB - LB <= solver tolerance
proven_optimal = bound_closed plus fully fathomed frontier
```

This preserves conservative proof semantics while explaining numerical `F=1.0x` before tree exhaustion.

## Real Circuit Matrix

```text
families: QFT, QAOA, GHZ, Grover, BV, VQE Real-Amplitudes
sizes: 8, 12, 16
audits: 18
audit pass: 18/18
methods per accepted circuit: H2, H3, KaHIP-Fast, Phase 2 MILP, CertiCut
method records: 90
Phase 2 MILP optimal: 18/18
CertiCut optimal: 18/18
```

## Transpilation Audit Observations

| Family | Original 2q form | CX result |
| --- | --- | --- |
| GHZ | native CX | unchanged counts `7,11,15` |
| BV | CZ | CX counts `3,5,7` |
| VQE real amplitudes | native CX | unchanged counts `21,33,45` |
| QAOA | RZZ | doubled CX counts `56,144,228` |
| QFT | opaque QFT gate | `68,150,264` CX after decomposition |
| Grover | opaque oracle gates | `2192,29190,234300` CX after decomposition |

For opaque high-level QFT/Grover gates, source `original_two_qubit_count=0`; `CX/original_2q` is undefined and intentionally not reported. Their audited post-transpilation CX count is the V1 optimization representation.

Grover expansion is extremely large by 16 qubits. It passed the logical CX audit but is unsuitable for unqualified runtime/scalability comparison at this rung; retain it as an ingestion stress artifact and bound future scale separately.

## Files

- `certicut/circuits/ingestion.py`
- `certicut/benchmark/checkpoints.py`
- `tests/test_ingestion.py`
- `scripts/run_phase6_3.py`
- `results/phase6_3_real_audits.jsonl`
- `results/phase6_3_real_records.jsonl`
- `requirements.txt`

## Verification

```text
56 passed in 16.51s
18/18 audits passed
90 real-circuit method records
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase6_3.py
```

## Next

Phase 6.5: gate-dependent QPD cost registry/correctness ladder before claims beyond CNOT-only. Phase 6.4 remains a separate Track B Qiskit practical-Qmax benchmark; do not merge its outcomes into Track A tables.

`ponytail:` real ingestion proves audited logical representation coverage, not hardware-aware cutting or abstract-algorithm partition optimality.
