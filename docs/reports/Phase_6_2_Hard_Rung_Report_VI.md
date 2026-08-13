# CertiCut Phase 6.2 Hard-Rung and Anytime Checkpoint Report

Ngày: 11/08/2026

## Trạng thái

PASS. Deterministic hard-rung Track A benchmark, KaHIP calibration, one-trajectory node checkpoints, raw ablations, and oracle certificate invariants are complete.

## Protocol

```text
Track: exact balanced K=2
sizes: 24, 26, 32
families: community, nearest-neighbor, random, dense, weighted-random, noisy-community
seeds: 5
instances: 90
node budget: 100
checkpoints: 0, 1, 5, 10, 30, 100
```

Checkpoint `0` is after H2 warm start and B2S root separation, before B&B expansion. Each instance runs one deterministic `node_limit=100` trajectory; named budgets forward-fill that same trajectory rather than re-running search six times.

`proven_optimal` is strict: only true when the B&B frontier is empty. A factor `1.0x` with nonempty frontier remains an exact numerical bound equality but is not reported as formal proof until fathoming completes.

## KaHIP Calibration

Separate calibration set:

```text
n = 24,26
families: random, dense, weighted-random
seeds: 3
instances: 18
```

| Mode | Oracle hits | Median factor | Median runtime |
| --- | ---: | ---: | ---: |
| Fast | `13/18` | `1.0x` | `0.000540s` |
| Eco | `11/18` | `1.0x` | `0.001205s` |
| Strong | `11/18` | `1.0x` | `0.016419s` |

Main benchmark uses **KaHIP-Fast**, selected before final hard-rung evaluation by quality first, then runtime.

## Main Matrix

```text
H2
H3
KaHIP-Fast
Phase 2 MILP
A0 = B0 + H0
A1 = B0 + H2
A2 = B2S-R + H0
A3 = B2S-R + H2 (CertiCut)
```

Results:

```text
720 method runs
540 checkpoint records
0 errors
90/90 Phase 2 oracle completions
0 checkpoint violations of LB <= OPT <= UB
```

## Heuristic Quality

Oracle-completed subset is all `90` instances.

| Method | Optimal hits | Median factor | p90 factor | Median runtime |
| --- | ---: | ---: | ---: | ---: |
| H2 | `65/90` | `1.0x` | `729x` | `0.010169s` |
| H3 | `72/90` | `1.0x` | `729x` | `0.011569s` |
| KaHIP-Fast | `77/90` | `1.0x` | `9x` | `0.000549s` |

KaHIP is the strongest independent feasible baseline on this CNOT-only hard rung. It still exposes no quantitative lower bound/certificate.

## Ablation

| Method | Proven optimal ≤100 nodes | Node-limited | Median nodes | Median root time | Median tree time |
| --- | ---: | ---: | ---: | ---: | ---: |
| A0 B0+H0 | `41/90` | `56` | `100` | `0s` | `2.059s` |
| A1 B0+H2 | `41/90` | `52` | `100` | `0s` | `2.072s` |
| A2 B2S-R+H0 | `90/90` | `0` | `1` | `0.260s` | `0.060s` |
| A3 B2S-R+H2 | `90/90` | `0` | `1` | `0.256s` | `0.063s` |

Interpretation: on this bounded corpus, metric root strengthening is the dominant proof/search contribution. H2 improves primal quality but does not materially change B0 proof count under the 100-node budget. Root separation adds cost, but removes the large B0 tree.

## Anytime Certificates: A3 CertiCut

| Expanded-node budget | Proven optimal | `F <= 1.01x` | `F <= 1.05x` | `F <= 1.10x` | Median F | p90 F |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | `0/90` | `39/90` | `39/90` | `39/90` | `4.074x` | `2886.955x` |
| 1 | `48/90` | `48/90` | `48/90` | `48/90` | `1.0x` | `729x` |
| 5 | `74/90` | `80/90` | `80/90` | `81/90` | `1.0x` | `1.086x` |
| 10 | `85/90` | `88/90` | `88/90` | `88/90` | `1.0x` | `1.0x` |
| 30 | `90/90` | `90/90` | `90/90` | `90/90` | `1.0x` | `1.0x` |
| 100 | `90/90` | `90/90` | `90/90` | `90/90` | `1.0x` | `1.0x` |

This is deterministic node-budget evidence, not wall-clock evidence. It supports a paper claim about early quantitative certificates within this exact balanced CNOT-only benchmark regime; it does not establish general scalability.

## Files

- `certicut/benchmark/checkpoints.py`
- `certicut/benchmark/runner.py`
- `certicut/circuits/benchmarks.py`
- `scripts/calibrate_kahip.py`
- `scripts/run_phase6_2.py`
- `scripts/summarize_phase6_2.py`
- `tests/test_checkpoints.py`
- `results/phase6_2_kahip_calibration.jsonl`
- `results/phase6_2_kahip_calibration_summary.json`
- `results/phase6_2_track_a_records.jsonl`
- `results/phase6_2_checkpoints.jsonl`
- `results/phase6_2_summary.json`

## Verification

```text
54 passed in 14.93s
720 hard-rung method runs, 0 errors
540 checkpoints, 0 oracle invariant violations
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\calibrate_kahip.py
.\.venv\Scripts\python.exe scripts\run_phase6_2.py
.\.venv\Scripts\python.exe scripts\summarize_phase6_2.py
```

## Next

Phase 6.3 must ingest real quantum circuits with explicit transpilation/gate-set verification. Phase 6.4 adds separate Track B Qiskit experiments. Phase 6.6 must use isolated process peak RSS and wall-clock protocol before paper-scale runtime/memory claims.

`ponytail:` all 90 instances prove by 30 nodes; this is an important bounded-regime result, not permission to call B2S-R generally scalable or remove the Phase 3C gap witness from the paper narrative.
