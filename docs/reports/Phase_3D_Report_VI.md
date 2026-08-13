# CertiCut Phase 3D Report

Ngày: 10/08/2026

## Trạng thái

PASS. B2S root separation đã được tích hợp vào certified B&B theo mode **B2S-R**: root cut pool được đóng băng và reuse ở mọi child node.

## B2S-R Architecture

```text
root: B2S separation -> immutable GlobalCutPool(version=1)
child: B2 LP + every root triangle cut -> no child separation
```

Root triangles là globally valid. Child LP reuse đúng cùng cut pool; không rebuild separation từ zero, không mutate pool, không suy đoán cached node bound tăng lên. Vì Phase 3D.1 pool immutable, logic certificate/queue Phase 3A giữ nguyên.

Node-level separation, pool mutation, cut-pool versioning, lazy node reoptimization chưa được đưa vào Phase 3D.1.

## Correctness

- Phase 3C weighted `n=8` gap witness: B2S-R completes and returns `LB=UB=Phase 2 OPT`.
- Witness `node_limit=0`: valid `LB <= OPT <= UB` certificate.
- B2S-R completion equals Phase 2 MILP on `100/100` seeded `n=4..8` instances.
- Full suite: `37 passed`.

## Hard Core

`results/phase3d_hard_instances.json` contains all `18` fractional B2S stress roots from Phase 3C:

```text
n = 26, 32, 40
random p=.10 / p=.50
noisy community
weighted random CNOT multiplicities
```

Controlled B0 vs B2S-R profile uses unchanged greedy incumbent, best-bound selection, most-fractional branching, exact balanced `K=2`, and `node_limit=100`.

## Tail Results

| Metric | B0 | B2S-R |
| --- | ---: | ---: |
| Hard instances | `18` | `18` |
| Optimal under 100 nodes | `1/18` | `15/18` |
| Node-limited | `17/18` | `3/18` |
| Median nodes | `100` | `7` |
| p75 nodes | `100` | `15` |
| p90 nodes | `100` | `100` |
| p95 nodes | `100` | `100` |
| Max nodes | `100` | `100` |
| Median total time | `1.161s` | `4.172s` |
| p90 total time | `1.854s` | `74.422s` |
| Max total time | `2.514s` | `161.960s` |

Node reduction is strongly positive for most instances, but not universal: observed reductions range from `0%` to `99%`.

## Root Cost vs Tree Cost

| B2S-R cost | Median | p90 | Max |
| --- | ---: | ---: | ---: |
| Root separation | `1.932s` | `12.461s` | `56.299s` |
| Child-node LP tree | `2.560s` | `69.308s` | `105.378s` |

Interpretation:

- Easy-to-medium hard instances: B2S-R removes most search but can lose wall-clock time to expensive root/child LPs.
- Tail instances: strengthened root cuts reduce search, but substantial trees remain and child LP cost dominates.
- This is Regime C. Branching/tree optimization is justified, but current fixed root pool is insufficient as a final branch-and-cut design.

## GNN Decision

**Conditional GO.** The precondition for learning-guided branching is now empirically present:

```text
B2S-R p90 nodes = 100
B2S-R p90 tree LP time = 69.308s
B2S-R p90 root time = 12.461s
```

Do not train GNN yet. First implement Phase 3D.2 node separation with a mutable global cut pool and versioned node reoptimization. Then profile hard tail again; proceed to strong branching only if tree cost remains material.

## Files

- `certicut/optimization/lp.py`: reusable B2 root cut-pool LP solver.
- `certicut/optimization/bnb.py`: `lp_variant="b2s_root"`, root/tree timing metrics.
- `tests/test_b2s_bnb.py`: witness, timeout, `100/100` oracle validation.
- `scripts/run_phase3d.py`: B0/B2S-R hard-core profile.
- `results/phase3d_hard_instances.json`
- `results/phase3d_hard_records.jsonl`
- `results/phase3d_summary.json`

## Verification

```text
37 passed in 12.46s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase3d.py
```

`ponytail:` B2S-R freezes root cuts; Phase 3D.2 upgrade is global-pool versioning plus node-level separation, not strong branching/GNN yet.
