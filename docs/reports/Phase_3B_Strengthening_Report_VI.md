# CertiCut Phase 3B.1-3 Report

Ngày: 10/08/2026

## Trạng thái

PASS. Hoàn tất primal/dual diagnostic, B1 compact reformulation, B2 metric/cut-polytope LP strengthening trên cùng corpus `175` instances.

## 3B.1 Diagnostic

Với completed B0 instance:

```text
F_root   = exp(UB0 - LB0)
F_primal = exp(UB0 - OPT)
F_dual   = exp(OPT - LB0)
F_root   = F_primal * F_dual
```

Invariant verified, maximum relative floating error: `3.78e-15`.

| B0 completed | Median primal factor | Median dual factor |
| --- | ---: | ---: |
| Overall, 147 instances | `1.0x` | `43.236x` |
| Community, 35 | `1.0x` | `1.0x` |
| Nearest-neighbor, 35 | `1.0x` | `2.655x` |
| QAOA ring, 35 | `1.0x` | `57.767x` |
| Random, 25 completed | `4.305e7x` | `2558.639x` |
| Dense, 17 completed | `4.305e7x` | `4.945e8x` |

Decision correction: lower-bound weakness dominates overall and especially dense, but the existing greedy warm start is also severely weak on completed random/dense instances. B2 targets the dual issue; future warm-start work remains justified.

## B1 Compact z

One assignment variable `z_i` replaces `y[i,0], y[i,1]`:

```text
z_i = 0 -> F0
z_i = 1 -> F1
z_0 = 0
x_ij >= z_i - z_j
x_ij >= z_j - z_i
n-Qmax <= sum(z_i) <= Qmax
```

Result: exact compact reformulation, not bound strengthening.

| Metric | B0 | B1 |
| --- | ---: | ---: |
| Optimal under 50 nodes | `147/175` | `146/175` |
| Median root LB | `4.394449` | `4.394449` |
| Median root factor | `57.767x` | `57.767x` |
| Median LP variables | `50` | `37` |
| Median LP constraints | `104` | `44` |
| Median expanded nodes | `3` | `4` |
| Median total LP time | `0.01508s` | `0.01567s` |

Verdict: **DROP as default solver**. B1 reduces model dimensions but brings no bound/node benefit; runtime win is topology-dependent, not robust at this scale. Keep implementation as compact reference only.

## B2 Metric Strengthening

Applicability: exact balanced `K=2`, `Qmax=ceil(n/2)` only.

Variables:

```text
z_i in [0,1]
x_ij in [0,1] for every complete-graph pair i<j
```

Objective counts only real interaction edges. Non-interaction `x_ij` have zero cost and encode global cut consistency.

Valid constraints:

```text
x_ij >= z_i-z_j
x_ij >= z_j-z_i
x_ij <= z_i+z_j
x_ij <= 2-z_i-z_j
sum(i<j) x_ij = floor(n^2/4)
triangle inequalities for every triple
```

Validation:

- Cardinality equality and all four triangle facets verified across all canonical 6-qubit toy `3+3` partitions.
- `B2 LB >= B0 LB`, `B2 LB <= Phase 2 OPT`: `100/100` seeded oracle cases.
- B2 completion matches Phase 2 oracle: `100/100`.
- B2 `node_limit=0` certificate contains Phase 2 optimum: `100/100`.
- B1 completion matches oracle: `100/100`.

Controlled corpus result:

| Metric | B0 | B1 compact | B2 metric |
| --- | ---: | ---: | ---: |
| Optimal under 50 nodes | `147/175` | `146/175` | `175/175` |
| Node-limited | `28` | `29` | `0` |
| Median root LB | `4.394449` | `4.394449` | `8.788898` |
| Median root factor | `57.767x` | `57.767x` | `1.0x` |
| Median expanded nodes | `3` | `4` | `1` |
| Median LP variables | `50` | `37` | `105` |
| Median LP constraints | `104` | `44` | `1823` |
| Median LP time | `0.01508s` | `0.01567s` | `0.02089s` |

B2 adds constraints but removes B&B search on this corpus. Dense is decisive: B0 `17/35` solved vs B2 `35/35`; median B0 nodes `50`, B2 `1`.

Verdict: **KEEP B2 for balanced exact K=2 research mode**. It is a profiling-scale all-triangle formulation, not final scalable mode. For large `n`, replace upfront all-triangle constraints with separated/lazy cuts before claiming scalability.

## Files

- `certicut/optimization/lp.py`: B0/B1/B2 dispatcher and formulations.
- `certicut/optimization/bnb.py`: LP-variant dispatch plus model-size profile metrics.
- `scripts/compare_phase3b_variants.py`: controlled corpus and diagnostics.
- `tests/test_lp_strengthening.py`: polyhedral and certificate regression.
- `results/phase3b_variant_records.jsonl`: raw B0/B1/B2 records.
- `results/phase3b_variant_summary.json`: aggregate result.

## Verification

```text
32 passed in 9.74s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\compare_phase3b_variants.py
```

## Scope

B2 is only valid when exact balanced two-fragment capacity applies. No K>2, no non-balanced at-most mode, no separation, no Qiskit baseline, no strong branching, no GNN.

`ponytail:` all-pair/all-triangle B2 ceiling is `n=24` profiling; upgrade path is branch-and-cut separation, not blindly materializing O(n^3) triangles at large n.
