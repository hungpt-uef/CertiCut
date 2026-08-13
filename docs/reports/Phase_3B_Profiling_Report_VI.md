# CertiCut Phase 3B Profiling Report

Ngày: 10/08/2026

## Trạng thái

PASS. Chỉ profiling B0 Phase 3A; không sửa relaxation, warm start, node selection, hay branching policy.

## Corpus

| Thuộc tính | Giá trị |
| --- | --- |
| Sizes | `8, 10, 12, 14, 16, 20, 24` |
| Families | random, nearest-neighbor, QAOA ring, dense, community |
| Seeds/family/size | `5` |
| Tổng instances | `175` |
| Mode | optimizer-only, CNOT-only, không statevector |
| Fragments | `K=2`, exact non-empty |
| Capacity | `Qmax=ceil(n/2)` |
| Budget | deterministic `node_limit=50` |

`K=2` cần `2*Qmax >= n`; các mức `0.40n/0.45n` không feasible, nên không thuộc corpus hợp lệ.

## B0 Results

| Metric | Median |
| --- | ---: |
| Completed optimal | `147/175` |
| Node-limited | `28/175` |
| Root LP LB | `4.394449154672439` |
| Initial greedy UB | `8.788898309344878` |
| Root additive log gap | `4.056414604313019` |
| Root factor certificate | `57.766822420804395x` |
| Expanded nodes | `3` |
| Generated nodes | `6` |
| Pruned by LP bound | `3` |
| LP solves | `7` |
| LP solve time | `0.0150s` |
| Total solve time | `0.0151s` |
| Root bound recovery, completed only | `0.5455` |

## Family Evidence

| Family | Node-limited | Median nodes | Root factor median | Root recovery, completed |
| --- | ---: | ---: | ---: | ---: |
| Community | `0/35` | `1` | `1.0x` | `1.000` |
| Nearest-neighbor | `0/35` | `2` | `2.655x` | `0.556` |
| QAOA ring | `0/35` | `2` | `57.767x` | `0.538` |
| Random | `10/35` | `20` | `3.05e12x` | `0.370` |
| Dense | `18/35` | `50` | `2.83e19x` | `0.286` |

## Decision

Evidence says LP bound quality, not runtime per LP or warm-start execution time, is B0 bottleneck on hard topologies:

- Dense/random root factors are astronomically loose.
- Dense/random have lowest root-bound recovery.
- Dense consumes full node budget in median.
- Community structure already solves at root; extra complexity cannot help this regime materially.

Next strengthening candidate: K=2 one-variable `z_i` formulation plus valid upper cut linearization, benchmarked against unchanged B0. Keep only if it improves certificates/nodes on hard families without violating Phase 3A oracle invariants.

## Instrumentation

`collect_profile=True` adds metrics only; default search/output remains Phase 3A behavior.

- Root LP LB, initial UB, root log gap/factor.
- Generated/pruned/integral nodes, max frontier.
- LP count/time, warm-start time, best-UB time, total solve time.
- Plot-ready B&B timeline remains unchanged.

## Files

- `certicut/circuits/benchmarks.py`
- `scripts/profile_phase3b.py`
- `tests/test_phase3b_profile.py`
- `results/phase3b_b0_records.jsonl`
- `results/phase3b_b0_summary.json`

## Verification

```text
27 passed in 5.29s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\profile_phase3b.py
```

`ponytail:` corpus is first profiling rung, 175 not 700 instances; expand seeds/budgets only after B1/B2 design exists, otherwise more runs repeat the same conclusion.
