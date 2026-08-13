# CertiCut Phase 6.6B E2/E3 Final Real-Circuit Report

Ngày: 11/08/2026

## Trạng thái

PASS. Frozen isolated protocol completed final real-circuit Track A CX-normalized and native-QPD CertiCut matrices.

## E2: Real CX-Normalized

```text
families: QFT, QAOA, GHZ, BV, VQE Real-Amplitudes
sizes: 8,12,16,20,24
records: 25
deadline: 60s safe boundary
optimal: 25/25
```

| n | Median end-to-end | Median optimizer | Median peak RSS |
| ---: | ---: | ---: | ---: |
| 8 | `0.799s` | `0.007s` | `156.81 MB` |
| 12 | `0.769s` | `0.019s` | `157.44 MB` |
| 16 | `0.756s` | `0.033s` | `159.21 MB` |
| 20 | `0.816s` | `0.109s` | `161.55 MB` |
| 24 | `0.939s` | `0.163s` | `163.24 MB` |

CX normalization/decomposition dominates E2 end-to-end time at small sizes. This is intentionally retained in preprocessing time, rather than attributed to the CertiCut optimizer.

## E3: Native-QPD

```text
families: QAOA, BV, VQE Real-Amplitudes
sizes: 8,12,16,20,24
records: 15
deadline: 60s safe boundary
optimal: 15/15
```

| n | Median end-to-end | Median optimizer | Median peak RSS |
| ---: | ---: | ---: | ---: |
| 8 | `0.026s` | `0.009s` | `107.61 MB` |
| 12 | `0.030s` | `0.011s` | `108.49 MB` |
| 16 | `0.052s` | `0.025s` | `110.27 MB` |
| 20 | `0.093s` | `0.072s` | `111.38 MB` |
| 24 | `0.148s` | `0.125s` | `113.50 MB` |

Native-QPD preserves QPD-supported numeric two-qubit gates. All source/audit metadata, representation fingerprints, and Qiskit 0.10 independent-QPD cost-model metadata remain in raw records.

## Scope

E2/E3 report CertiCut isolated runtime/memory only. They do not replace the H2/H3/KaHIP/MILP method matrices of earlier fixed-size experiments. Grover is excluded from the main final scale because its opaque-gate decomposition expands to hundreds of thousands of CX instructions by n=16; it remains a documented representation stress case.

## Files

- `certicut/benchmark/isolated.py`
- `scripts/run_phase6_6b_real.py`
- `scripts/summarize_phase6_6b_real.py`
- `results/phase6_6b_e2_real_cx.jsonl`
- `results/phase6_6b_e3_native_qpd.jsonl`
- `results/phase6_6b_real_summary.json`

## Verification

```text
68 passed in 21.48s
40/40 isolated real records optimal
```

## Interpretation

The final real matrices reinforce the representation result: optimizer time must be reported separately from circuit decomposition/transpilation preprocessing. Native-QPD removes a substantial representation-conversion cost for suitable circuits, while its sampling-overhead semantics remain explicitly tied to Qiskit 0.10 independent QPD decompositions.

`ponytail:` E2/E3 are fixed-family/fixed-source matrices, not a statistical real-circuit distribution claim. Keep their scope separate from E1 synthetic 420-instance evidence.
