# CertiCut Phase 3D.2 Report

Ngày: 10/08/2026

## Trạng thái

PASS correctness. **DROP B2S-N as current default performance policy.** Mutable cut-pool/versioning works, but node-level separation does not reduce the hard tail under controlled depth-limited policy and increases runtime.

## B2S-N Architecture

```text
GlobalCutPool = canonical set[(i,j,k,facet)] + monotonic version
node = fixed assignments + LP lower bound + pool_version

pop stale node:
  re-solve with current pool before prune/integral/branch

child at depth <= 1:
  LP + top_k=100 triangle separation, max_rounds=3
  promote newly found globally valid cuts to pool

deeper child:
  reuse latest pool, no new separation
```

This is lazy reoptimization. Cached stale bounds remain valid lower bounds until re-solved; global certificate continues to use stored frontier bounds conservatively.

## Correctness

- B2S-N completion equals Phase 2 MILP on `100/100` seeded small instances.
- B2S-N node-limit certificate contains exact MILP optimum.
- Pool accepts unique canonical facets only.
- Stale nodes are re-solved before B&B decisions when pool version changed.
- Full suite: `40 passed`.

## Full-Node Boundary

Initial unrestricted node separation (`top_k=100`, `max_rounds=3` every depth) exceeded practical runtime even with a `30`-node hard-core budget. It was stopped; this is an empirical cost boundary, not a correctness failure.

Controlled D2 profiling therefore uses depth-limited separation `depth <= 1`. Root remains fully separated as B2S-R.

## D0/D1/D2 Hard-Tail Comparison

Hard core: `18` Phase 3C fractional roots, `n=26,32,40`, same incumbent/branching/best-bound, `node_limit=30`.

| Metric | D0 B0 | D1 B2S-R | D2 B2S-N depth<=1 |
| --- | ---: | ---: | ---: |
| Optimal | `0/18` | `13/18` | `13/18` |
| Node-limited | `18/18` | `5/18` | `5/18` |
| Median nodes | `30` | `7` | `7` |
| p75 nodes | `30` | `15` | `13` |
| p90 nodes | `30` | `30` | `30` |
| Median total time | `1.219s` | `3.900s` | `4.958s` |
| p90 total time | `2.345s` | `28.822s` | `36.039s` |
| p95 total time | `2.416s` | `60.499s` | `65.842s` |

## Node-Separation Diagnostics

| D2 metric | Median | p90 | Max |
| --- | ---: | ---: | ---: |
| Node cuts discovered | `8.5` | `411` | `537` |
| Node separation time | `1.447s` | `8.878s` | `16.274s` |
| Stale nodes reoptimized | `0.5` | `4` | `4` |
| Reoptimization LB gain | `0.0` | `<3e-13` | `<2e-12` |

The global pool receives node cuts, but those cuts produce no material bound gain for subsequently popped stale nodes in this experiment. Thus cross-node cut reuse is currently weak, while its separation cost is concrete.

## Decision

```text
KEEP: GlobalCutPool abstraction, canonical cuts, versioned lazy reoptimization.
KEEP: B2S-R root-only separation as default strengthened B&B mode.
DROP: full-node B2S-N policy; pathological runtime.
DROP: depth<=1 B2S-N policy; no completion/tail gain, slower runtime.
```

No further separation engineering before evaluating primal quality and strong branching. Branching remains justified because B2S-R hard tail still reaches node limit; node-level cuts are not the right next investment under current data.

## Files

- `certicut/optimization/lp.py`: initial cut pools, bounded separation rounds, canonical active cuts.
- `certicut/optimization/bnb.py`: mutable `GlobalCutPool`, node pool versions, stale lazy reoptimization, depth-limited policy, D2 metrics.
- `tests/test_b2s_node_bnb.py`: B2S-N oracle/certificate/pool coverage.
- `scripts/run_phase3d.py`: D0/D1/D2 tail comparison.
- `results/phase3d_hard_records.jsonl`
- `results/phase3d_summary.json`

## Verification

```text
40 passed in 17.31s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase3d.py
```

`ponytail:` cut-pool versioning stays even though D2 is dropped; it is required infrastructure if future valid inequalities or branch-and-cut policies demonstrate positive cross-node reuse.
