# E16 Baseline Upgrade Report

## Delivered

- `Greedy-Swap`: existing exact-capacity QPD local-search baseline, now wall-clock bounded.
- `Froehler-KL-count`: K-way pairwise locked-pass KL adaptation using gate-occurrence counts. It is explicitly an adaptation, not a reproduction of the full Fröhler framework.
- `KL-QPD`: same K-way KL implementation using aggregate independent-QPD log weights.
- `KaHIP-QPD+repair`: QPD-scaled KaHIP seed, minimum-delta exact-capacity repair, QPD swap refinement, canonical evaluation.
- Central evaluator: `certicut/evaluation/canonical.py`; matched methods cannot self-report objectives.
- Open records: `certified_upper_factor_log10`; closed records: `regret_log10`. These fields are never mixed.
- Restricted independent gate-only exact oracle: direct occurrence sums, exact capacities, `n <= 10`. This validates the CertiCut restriction only; it is not a Brandhofer reproduction.

## Validation

- Relevant regression tests: `14 passed`.
- Restricted oracle: 12 heterogeneous instances, including K=3; direct gate sum, aggregate graph sum, and SCIP all matched. Maximum absolute discrepancy: `3.552713678800501e-15`.
- Manuscript: `pdflatex -> bibtex -> pdflatex -> pdflatex` succeeds. No undefined citations or LaTex errors.

## Frozen Corpus Results

All matched methods returned exact-capacity partitions: E6 `144/144`, E9 `576/576`, E10 `144/144` method records.

| Corpus | Result |
|---|---|
| E6 | KL-QPD optimal `36/36`; KL-count `20/36`; Greedy-Swap `34/36`; KaHIP-QPD+repair `35/36`. |
| E9 closed subset | KL-QPD optimal `68/101`, median/p90 `log10 R = 0.00/2.94`; KL-count `23/101`, `1.56/5.01`; Greedy-Swap `23/101`, `1.45/10.52`; KaHIP-QPD+repair `51/101`, `0.00/1.47`. |
| E10 closed subset | KL-QPD optimal `15/15`; KL-count `3/15`; Greedy-Swap `11/15`; KaHIP-QPD+repair `14/15`. |

KaHIP median E9 runtime: `5.89s`; it remains contextual for runtime because the native binding has no hard timeout.

## Corpus Protocol

Run:

```powershell
& ".venv\Scripts\python.exe" scripts/run_baseline_suite.py --corpus both --time-limit-s 0.1
```

Outputs:

```text
results/upgrade_2026/e16_baseline_suite/e9.jsonl
results/upgrade_2026/e16_baseline_suite/e10.jsonl
results/upgrade_2026/e16_baseline_suite/summary.json
```

`Greedy-Swap`, `KL-count`, and `KL-QPD` use the declared 0.1 s search budget. KaHIP's Python binding exposes no native wall-clock limiter; its post-KaHIP repair/refinement uses the declared budget, but native KaHIP runtime is reported separately and cannot be claimed wall-clock matched.

## Scope Boundaries

- Brandhofer: exact contextual baseline only. Full gate/wire/ancilla/classical-communication model not implemented or claimed.
- Nakamura `L_Q`, Fröhler full, FitCut: contextual comparators. Different objective/feasible model; excluded from matched-regret table.
- `KaHIP` integer scaling: `round(10^6 w_e)`. Test verifies per-edge reconstruction error at most `0.5 / 10^6`.
