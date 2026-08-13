# E7 Frozen Heterogeneous-QPD Scaling Report

Date: 2026-08-12

## Decision-Relevant Result

Full E7 **does not support** a custom-CERTICUT solver-superiority claim.

Matched SCIP G0 dominates CERTICUT on this frozen heterogeneous corpus at every measured checkpoint. Publication framing: log-domain formulation and solver-tolerance model-factor semantics are backend-independent; CERTICUT is a reference specialized implementation, mature MIP is the stronger practical engine on this corpus.

Do not report custom solver speed/bound superiority.

## Protocol Integrity

- Freeze: `results/phase12_e7_protocol_frozen.json`
- Frozen before full execution: `2026-08-12T12:14:51+07:00`
- Corpus: 200 records = 5 deterministic heterogeneous families x `n={20,24,32,40}` x 10 seeds.
- Gate rule: occurrence-index cyclic `CX`, `CZ`, `iSWAP`, `RZZ(pi/8)`, `RZZ(pi/4)`, `RZZ(pi/2)`.
- Scope: exact-balanced static logical K=2 gate cutting, independent per-gate QPD, fixed instruction representation.
- Threads: `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`.
- Independent budgets: 2, 10, 60 s. Graph construction excluded.
- Methods: CERTICUT B2S-root+H2; SCIP G0 basic; SCIP G1 cardinality; SCIP G2 full triangles.
- CERTICUT: `solver_tolerance`. SCIP: `SCIP numerics/feastol`.

Raw schema validation:

```text
200 unique records; all prescribed checkpoints and thread limit present.
```

| Evidence | SHA-256 |
|---|---|
| `results/phase12_e7_heterogeneous_scaling.jsonl` | `0F1964C8B9DADF0E346B2601E7F9DF440E30F7E9D66DEFC65CBF52BBFD975C2D` |
| `results/phase12_e7_protocol_frozen.json` | `408AF9E7F67EEC9A552F6BF673F2854D02C12C068A1161FFBFF016A7C6E14BED` |
| Processed summary | `results/phase12_e7_heterogeneous_scaling_summary.json` |

## Main Factors

`F = exp(UB-LB)`. Solver-tolerance numerical quantities. Not independently verified numerical proofs.

| Time | Method | F <= 1.01 | F <= 1.10 | Closed | Median F | p90 F |
|---:|---|---:|---:|---:|---:|---:|
| 2 s | CERTICUT | 160/200 | 160/200 | 160/200 | 1 | 62.13 |
| 2 s | SCIP G0 | 199/200 | 199/200 | 199/200 | 1 | 1 |
| 2 s | SCIP G1 | 111/200 | 111/200 | 111/200 | 1 | 2.45e12 |
| 2 s | SCIP G2 | 108/200 | 108/200 | 108/200 | 1 | 1.74e16 |
| 10 s | CERTICUT | 184/200 | 184/200 | 184/200 | 1 | 1 |
| 10 s | SCIP G0 | 200/200 | 200/200 | 200/200 | 1 | 1 |
| 10 s | SCIP G1 | 186/200 | 186/200 | 186/200 | 1 | 1 |
| 10 s | SCIP G2 | 158/200 | 158/200 | 158/200 | 1 | 345.75 |
| 60 s | CERTICUT | 199/200 | 199/200 | 199/200 | 1 | 1 |
| 60 s | SCIP G0 | 200/200 | 200/200 | 200/200 | 1 | 1 |
| 60 s | SCIP G1 | 196/200 | 196/200 | 196/200 | 1 | 1 |
| 60 s | SCIP G2 | 183/200 | 183/200 | 183/200 | 1 | 1 |

## Time To Threshold

First fixed checkpoint achieving `F <= threshold`.

| Method | F threshold | 2 s | 10 s | 60 s | Not reached |
|---|---:|---:|---:|---:|---:|
| CERTICUT | 1.01 | 160 | 24 | 15 | 1 |
| SCIP G0 | 1.01 | 199 | 1 | 0 | 0 |
| SCIP G1 | 1.01 | 111 | 75 | 10 | 4 |
| SCIP G2 | 1.01 | 108 | 50 | 25 | 17 |
| CERTICUT | 1.10 | 160 | 24 | 15 | 1 |
| SCIP G0 | 1.10 | 199 | 1 | 0 | 0 |
| SCIP G1 | 1.10 | 111 | 75 | 10 | 4 |
| SCIP G2 | 1.10 | 108 | 50 | 25 | 17 |

## Size Detail

`F <= 1.01` at 2 s / closed at 60 s. Denominator 50 each size.

| n | CERTICUT | SCIP G0 | SCIP G1 | SCIP G2 |
|---:|---|---|---|---|
| 20 | 50/50 | 50/50 | 50/50 | 44/50 |
| 24 | 50/50 | 50/50 | 34/50 | 38/50 |
| 32 | 37/50, 50/50 | 50/50 | 15/50, 50/50 | 26/50, 50/50 |
| 40 | 23/50, 49/50 | 49/50, 50/50 | 12/50, 46/50 | 0/50, 33/50 |

CERTICUT closes all evaluated `n=20,24,32` records by 60 s; difficulty concentrates at `n=40`.

## Incumbent Agreement

At 60 s, SCIP G0 is the best observed incumbent reference.

- CERTICUT matches G0 UB: `199/200`.
- SCIP G1 matches G0 UB: `198/200`.
- SCIP G2 matches G0 UB: `189/200`.

CERTICUT's open record:

| Family | n | Seed | UB | LB | F | G0-UB delta |
|---|---:|---:|---:|---:|---:|---:|
| `dense_shuffled` | 40 | 8 | 70.50844 | 68.69586 | 6.1262 | 1.00041 |

This forbids claims that CERTICUT closes all heterogeneous cases through n=40, or always finds the best observed incumbent.

## Interpretation

1. Core contribution survives: exact weighted-bisection reduction plus primal/lower-bound to model-overhead factor semantics.
2. Custom tree manager is not the contribution to sell. SCIP G0 gives better early factors, 200/200 closures by 10 s.
3. G1/G2 do not show that static cardinality/full triangle additions strengthen a mature MIP engine under these formulations and budgets.
4. CERTICUT remains a reproducible reference solver and semantic reporting layer; mature MIP better instantiates this framework here.
5. E7 supports heterogeneous-QPD evaluation through n=40 on this generated corpus only. No hardware, joint-QPD, general-K, physical-shot claim.

## Required Manuscript Direction After E8

- E7 main experiment, not appendix.
- SCIP G0 main matched baseline.
- Report UB/LB/F, thresholds, time-to-threshold, closure. Not closure alone.
- State: SCIP G0 closes `200/200` by 10 s; CERTICUT closes `199/200` by 60 s.
- Remove solver-speed/specialized-search advantage claims.
- Use `solver-tolerance factor bound` and `model-overhead factor`, never formal numerical proof.
- Preserve this negative result.

## Next Gate

Freeze E8 before execution. Use strong reversal, moderate reversal, preferably no-reversal negative control. Report all predeclared observables and seeds. Do not alter E7 protocol/raw evidence.
