# CertiCut Phase 6.6B E1 Final Synthetic Track A-CX Report

Ngày: 11/08/2026

## Trạng thái

PASS. Final isolated E1 synthetic CertiCut corpus is complete with resumable raw records, inclusive safe-deadline timing, wall-clock certificate snapshots, and peak process working-set measurements.

## Manifest

```text
experiment: E1_core_synthetic_track_a_cx
Track: exact balanced K=2, CNOT-only
families: community, nearest-neighbor, QAOA ring, random, dense, weighted-random, noisy-community
sizes: 16,20,24,26,32,40
seeds: 10
instances: 420
requested safe deadline: 60s
worker: fresh isolated process per instance
```

The append-only runner persists each finished record immediately. No result is omitted when a run reaches the safe deadline.

## Completion

| Status | Count |
| --- | ---: |
| Proven optimal | `417/420` |
| Safe time-limit certificate | `3/420` |
| Worker error | `0/420` |

The three non-completed instances retain valid returned `LB`, `UB`, and factor records. They are not treated as failed or discarded.

## Wall-Clock Certificates

One 60-second trajectory per instance produces all requested-time snapshots. `bound_closed` means numerical gap closure in tolerance; `proven_optimal` additionally requires an empty frontier.

| Requested time | Available certificate | Proven | Bound closed | `F<=1.01x` | `F<=1.05x` | `F<=1.10x` | Median F | p90 F |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.5s | `278/420` | `245/420` | `245/420` | `245/420` | `245/420` | `245/420` | `1.0x` | `1.710x` |
| 1s | `331/420` | `292/420` | `292/420` | `292/420` | `292/420` | `293/420` | `1.0x` | `1.718x` |
| 2s | `371/420` | `343/420` | `343/420` | `343/420` | `343/420` | `343/420` | `1.0x` | `1.0x` |
| 5s | `386/420` | `365/420` | `365/420` | `365/420` | `365/420` | `366/420` | `1.0x` | `1.0x` |
| 10s | `417/420` | `388/420` | `388/420` | `388/420` | `388/420` | `388/420` | `1.0x` | `1.0x` |
| 30s | `420/420` | `408/420` | `408/420` | `408/420` | `408/420` | `408/420` | `1.0x` | `1.0x` |
| 60s | `420/420` | `417/420` | `417/420` | `417/420` | `417/420` | `417/420` | `1.0x` | `1.0x` |

This is a true inclusive algorithm timeline: the timer starts before graph processing, H2, B2S root LP/separation, and tree search. Before the first completed safe LP/node boundary, a certificate is marked unavailable rather than backfilled from a later state. Requested deadlines and actual event return times are separate raw fields.

## Isolated Timing and Memory

| n | Optimal | Median preprocess | Median optimizer | Median end-to-end | Median peak RSS | p90 peak RSS |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | `70/70` | `0.00068s` | `0.04128s` | `0.04215s` | `109.18 MB` | `109.79 MB` |
| 20 | `70/70` | `0.00081s` | `0.09851s` | `0.09925s` | `111.18 MB` | `111.97 MB` |
| 24 | `70/70` | `0.00090s` | `0.22556s` | `0.22627s` | `114.24 MB` | `115.07 MB` |
| 26 | `70/70` | `0.00109s` | `0.65069s` | `0.65265s` | `116.28 MB` | `116.97 MB` |
| 32 | `70/70` | `0.00133s` | `0.96126s` | `0.96203s` | `123.20 MB` | `125.75 MB` |
| 40 | `67/70` | `0.00151s` | `7.80527s` | `7.80842s` | `135.99 MB` | `138.75 MB` |

Preprocessing is negligible throughout this corpus. The optimizer, dominated by root strengthening and subsequent exact search, becomes the bottleneck at n=40. This is empirical timing data, not an asymptotic scaling claim.

## Scope

E1 is the final CNOT-only Track A-CX CertiCut wall-clock corpus. It does not replace:

```text
E2 real CX-normalized circuit evaluation
E3 native-QPD representation evaluation
E4 Qiskit practical-Qmax Track B evaluation
```

It also does not compare equal wall-clock behavior against Qiskit. Qiskit native API runs remain reported under their own backjump budget and actual-runtime protocol.

## Files

- `certicut/benchmark/isolated.py`
- `scripts/run_phase6_6b.py`
- `scripts/summarize_phase6_6b.py`
- `tests/test_final_protocol.py`
- `results/phase6_6b_e1_certicut.jsonl`
- `results/phase6_6b_e1_wallclock_checkpoints.jsonl`
- `results/phase6_6b_e1_summary.json`

## Verification

```text
68 passed in 29.29s
420/420 isolated E1 records
0 worker errors
```

## Next

Run the same frozen isolated protocol for E2 real CX-normalized and E3 native-QPD matrices, then aggregate figures/tables without changing any manifest or method semantics.

`ponytail:` n=40 produces the first visible root/search tail. Do not extend to n=48 in the main corpus before comparing this cost against final real/native evidence.
