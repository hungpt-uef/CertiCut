# CertiCut Phase 3E Report

Ngày: 11/08/2026

## Trạng thái

PASS. Primal warm-start strengthening sharply improves initial feasible cut plans while preserving certified B2S-R B&B semantics.

## Variants

```text
H0: existing incremental greedy
H1: deterministic multi-start greedy
H2: H1 + balanced weighted pair-swap local refinement
H3: spectral Fiedler balanced split + pair-swap refinement, best-of all candidates
```

All variants are deterministic, preserve `q0 -> F0`, preserve exact balanced two-fragment capacity, and recompute objective from `InteractionGraph`. H2/H3 use only balanced swaps, so feasibility is never relaxed.

## Correctness

- H0-H3 feasible and deterministic on `100/100` seeded `n=4..8` instances.
- Every candidate satisfies `OPT <= UB_H <= UB_H0`.
- B2S-R completion reaches the same Phase 2 MILP optimum under every warm start on `40/40` seeded instances.
- No certificate, LP bound, B&B queue, branch choice, or pruning rule changed.

## Controlled Profile

Representative hard core: `15` fractional B2S-R roots from `n=26,32`; `n=40` was excluded from repeated four-variant execution because Phase 3D already established its expensive tail. All variants use B2S-R, `node_limit=30`, best-bound, most-fractional branching.

| Metric | H0 | H1 | H2 | H3 |
| --- | ---: | ---: | ---: | ---: |
| Optimal | `13/15` | `13/15` | `13/15` | `14/15` |
| Node-limited | `2/15` | `2/15` | `2/15` | `1/15` |
| Median initial UB log | `175.778` | `169.186` | `109.861` | `109.861` |
| Median primal factor to final UB | `2.06e14x` | `3.14e10x` | `1.0x` | `1.0x` |
| p90 primal factor to final UB | `6.96e65x` | `2.25e34x` | `81x` | `81x` |
| Median warm-start time | `0.00013s` | `0.00062s` | `0.0170s` | `0.0211s` |
| Median nodes | `5` | `5` | `3` | `3` |
| p90 nodes | `13` | `13` | `13` | `7` |
| Median total time | `1.002s` | `0.976s` | `0.964s` | `0.941s` |

For node-limited records, `initial_primal_factor_to_final` is an incumbent-improvement diagnostic rather than an exact factor-to-OPT, because final UB may remain above OPT. Completed records use final proven UB equal to OPT.

## Interpretation

- H1 improves greedy UB cheaply but leaves the B&B tree unchanged.
- H2 pair swaps repair greedy placement errors: median initial plan reaches the final optimum on this representative core.
- H3 adds spectral initialization without material extra cost and reduces p90 nodes from `13` to `7`; it solves one extra hard-core instance under the same node budget.
- The heuristic cost is milliseconds, far below root separation and tree-LP time, so primal strengthening has positive ROI.

## Decision

```text
DROP: H0 as default warm start.
DROP: H1 as standalone default; cheap but weak tree effect.
KEEP: H2 as default deterministic warm start.
KEEP: H3 as best-primal research mode; modest extra cost, improved hard-tail completion.
```

Hard tail remains: H3 p90 still has `7` nodes and one instance reaches `30` nodes. Phase 4 strong branching study is justified after this primal confounder is controlled.

## Files

- `certicut/optimization/heuristics.py`: H0-H3 constructors, pair-swap refinement, spectral split.
- `certicut/optimization/bnb.py`: warm-start variant selection.
- `tests/test_warm_starts.py`: feasibility, determinism, oracle independence.
- `scripts/run_phase3e.py`: controlled hard-core profile.
- `results/phase3e_records.jsonl`
- `results/phase3e_summary.json`

## Verification

```text
42 passed in 19.15s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase3e.py
```

`ponytail:` H3 uses dense NumPy eigendecomposition, validated through `n=32` repeated profile only; keep H2 as default and profile H3 on n=40+ before any scalability claim.
