# CertiCut Phase 6.5B Native-QPD Representation Report

Ngày: 11/08/2026

## Trạng thái

PASS. Paired CX-normalized and native-QPD representations are built from the same deterministic MQT source circuits and produce materially different sampling-aware optima for QAOA.

## Paired Protocol

Each pair starts from one source circuit with a shared source SHA-256 fingerprint and parameter binding:

```text
MQT Bench 2.2.2
all source parameters = pi/4
```

Representations:

```text
R_CX:
  transpile basis [rz, sx, x, cx]
  all 2q instructions are CX

R_NATIVE:
  preserve every supported numeric 2q operation
  recursively decompose only operations with arity > 2
  audit every final 2q operation with QPDBasis.from_instruction
```

Native audit passes only if every final operation has arity at most two and every two-qubit gate receives a numeric Qiskit QPD cost. Both modes use:

```text
cost_model = qiskit_qpd_0.10_independent
```

## Matrix

```text
sources: QAOA, BV, VQE Real-Amplitudes
sizes: 8, 12, 16
source circuits: 9
representations: 18
audits passed: 18/18
methods per representation: H2, H3, MILP, CertiCut
method runs: 72
MILP optimal: 18/18
CertiCut optimal: 18/18
```

KaHIP is excluded: real native QPD edge weights are floating point and no quantization protocol is part of this phase.

## Controls and QAOA Result

| Family | n | CX 2q | Native 2q | Native gate | `J*_CX` | `J*_native` | `Gamma_CX/Gamma_native` |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| QAOA | 8 | 56 | 28 | RZZ | 52.733 | 26.367 | `5.31e11` |
| QAOA | 12 | 144 | 72 | RZZ | 114.256 | 57.128 | `6.46e24` |
| QAOA | 16 | 228 | 114 | RZZ | 158.200 | 79.100 | `2.25e34` |
| BV | 8/12/16 | 3/5/7 | 3/5/7 | CZ | 0 | 0 | `1x` |
| VQE real amplitudes | 8 | 21 | 21 | CX | 6.592 | 6.592 | `1x` |
| VQE real amplitudes | 12 | 33 | 33 | CX | 6.592 | 6.592 | `1x` |
| VQE real amplitudes | 16 | 45 | 45 | CX | 6.592 | 6.592 | `1x` |

QAOA gives the intended representation-sensitive result: native RZZ preserves 114 native 2q instructions at n=16 while CX normalization has 228; the QPD-aware optimum differs by `79.100` log units under the respective independent-QPD representations.

BV is a CZ/CX equal-overhead control; VQE is a native-CX negative control. Both behave consistently with expectation.

## Interpretation

The paired experiment establishes:

```text
same source algorithmic circuit
different legal transpiled/native gate representation
different interaction weights and sampling-overhead optimum
```

The ratio is an estimate under the respective Qiskit-compatible independent-QPD representations. It does not claim an intrinsic shot-cost ratio for the abstract algorithm or a joint-QPD optimum.

For QAOA at fixed parameter pi/4, the change combines two effects:

```text
fewer crossed native interactions: RZZ versus CX decomposition
lower native per-gate QPD log cost: log(3+2sqrt(2)) versus log(9)
```

## Files

- `certicut/circuits/ingestion.py`
- `tests/test_ingestion.py`
- `scripts/run_phase6_5b.py`
- `results/phase6_5b_native_audits.jsonl`
- `results/phase6_5b_native_records.jsonl`
- `results/phase6_5b_representation_comparison.json`

## Verification

```text
65 passed in 17.54s
9 paired sources
18/18 representation audits passed
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase6_5b.py
```

## Next

Phase 6.4: separate practical-Qmax Qiskit gate-only Track B benchmark. Keep native-QPD Track A results separate from CX/KaHIP tables unless a float-weight KaHIP protocol is explicitly introduced.

`ponytail:` source parameters are fixed at pi/4 for paired reproducibility. Angle sweeps are a future sensitivity study, not a general QAOA claim.
