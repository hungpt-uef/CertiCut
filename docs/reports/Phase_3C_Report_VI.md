# CertiCut Phase 3C Report

Ngày: 10/08/2026

## Trạng thái

PASS. Đã xác định B2 hardness boundary, tìm counterexample nhỏ, và thay all-triangle root formulation bằng B2S separated metric LP.

## Root Diagnosis: B2 Is Not Generally Exact

Trên corpus `175` B2 instances:

| Metric | Count |
| --- | ---: |
| Root bound exact, `LBroot=OPT` | `143/175` |
| Root LP integral | `143/175` |
| B2S bound equals B2 all-triangle bound | `175/175` |

Trong corpus này root-bound exact và root-LP-integral trùng nhau. Đây là empirical observation, không phải theorem.

| Family | Root exact | Root integral |
| --- | ---: | ---: |
| Community | `35/35` | `35/35` |
| QAOA ring | `35/35` | `35/35` |
| Nearest-neighbor | `25/35` | `25/35` |
| Random | `25/35` | `25/35` |
| Dense | `23/35` | `23/35` |

## B2 Gap Witness

Systematic search on weighted random CNOT graphs found a deterministic counterexample:

```text
n = 8
density = 0.50
trial = 7
OPT = 28.56391950537085
B2 root LB = 27.685029674436333
gap = 0.8788898309345186
fractional z variables = 7
max fractionality = 0.4
```

Artifact: `results/b2_gap_witness.json`. It records every aggregate edge and CNOT multiplicity. This disproves any accidental inference that B2 makes balanced weighted bisection trivial.

## B2S: Separated Metric LP

Initial model:

```text
z variables
complete-pair x variables
XOR envelope
balanced cardinality equality
no triangle constraints
```

Loop:

```text
solve LP
find violated three triangle inequalities or perimeter facet
add all violations, or top-k by magnitude
rebuild and solve
stop when no violation remains
```

Only root separation is implemented. Node-level separation/branch-and-cut remains out of scope.

## B2 vs B2S

On the existing 175 instance corpus:

```text
LB_B2S = LB_B2: 175/175
median separation rounds: 2
median active triangle facets: 150
```

Static B2 has roughly `1,823` median constraints. B2S reaches the same root bound with far fewer active triangle constraints; additional LP solves are traded for a smaller final cut pool.

## Stress Boundary

Root-only B2S stress corpus:

```text
n = 26, 32, 40
regimes = random p=.10, random p=.50, noisy community, weighted random
2 seeds/regime/size
24 instances
top_k = 500 separation policy
```

| Metric | Result |
| --- | ---: |
| Integral roots | `6/24` |
| Fractional roots | `18/24` |
| Median active triangles | `2796.5` |
| Median LP time | `1.3746s` |
| Max constraints | `9128` |

Conclusion: search/fractionality returns at larger/harder regimes. GNN/strong branching remains potentially relevant, but only after root B2S is integrated into B&B and hard-node corpus is characterized.

## Validation

- B2S all-violated equals B2 all-triangle: `100/100` small oracle instances.
- B2S `LB <= Phase 2 OPT`: `100/100`.
- Top-k and all-violated policies agree on toy-scale stress circuit.
- Existing Phase 0-3B suite remains valid.

## Files

- `certicut/optimization/lp.py`: B2S separation, triangle violation detection, root fractionality metrics.
- `scripts/run_phase3c.py`: root diagnostics, stress boundary, witness search.
- `tests/test_phase3c.py`: B2S equivalence tests.
- `results/phase3c_root_records.jsonl`
- `results/phase3c_stress_records.jsonl`
- `results/phase3c_summary.json`
- `results/b2_gap_witness.json`

## Verification

```text
34 passed in 12.30s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase3c.py
```

## Decision

Keep B2S as scalable-root candidate. Do not claim all-triangle B2 scalable. Next technical step: integrate root B2S into certified B&B, then profile whether trees remain on witness/stress instances before deciding strong branching/GNN.

`ponytail:` B2S currently rebuilds LP each round, root only, maximum validated stress size `n=40`; upgrade path is cut-pool reuse and node-level separation, not a larger static triangle matrix.
