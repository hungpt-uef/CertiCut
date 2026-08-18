# CertiCut Revision Response and Implementation Report

Date: 2026-08-12

## Scope

This report responds to the supplied major-revision review. It distinguishes completed implementation, frozen evidence, smoke evidence, and unresolved requirements. No smoke result is promoted to a paper-level claim.

## Executive Result

- Core log-domain weighted-bisection reduction remains correct within static, balanced, gate-only, K=2, independent-QPD scope.
- Numeric output is now labelled `solver_tolerance`; no formal numerical certificate is claimed.
- Matched SCIP checkpoint API added.
- Heterogeneous-QPD scaling runner added.
- Equal-shot finite-sampling validation API and runner added.
- Full test suite: `121 passed in 22.98s`.
- Manuscript PDF not rebuilt: `pdflatex` unavailable on this host.

## Reviewer Issues

| Priority | Issue | Status | Evidence / action |
|---|---|---|---|
| P0 | Floating-point certificate overclaim | Addressed framing; not formal verification | `certicut/optimization/certificate.py`; `paper/certicut.tex` |
| P0 | Conservative numerical lower bound | Partially addressed | Report has `numerical_safety_margin_log`, conservative LB/factor fields. Margin is declared, not independently verified. Directed rounding/rational LP verification remains required for a formal proof. |
| P0 | Matched mature-MIP comparison | Full E7 complete | SCIP G0 closes 200/200 by 10 s, versus CERTICUT 184/200 at 10 s and 199/200 at 60 s. See `Phase_12_E7_Frozen_Heterogeneous_Scaling_Report.md`. |
| P0 | Large heterogeneous scaling | Full E7 complete | 200 frozen heterogeneous-QPD records through n=40; no custom-solver superiority claim is supported. |
| P1 | Finite-shot validation | Full E8 complete | Strong reversal improves RMSE for both observables; moderate reversal is mixed/inconclusive; control distributions are identical. See `Phase_12_E8_Frozen_Finite_Shot_Report.md`. |
| P1 | Artifact reproducibility | Improved local artifact | Deterministic generators/runners, pinned-thread isolated runner, test coverage. Immutable anonymous archive still external/release-process work. |
| P1 | Novelty framing | Addressed | Title, abstract, contributions, limits changed to solver-tolerance/balanced-K2 specialization. |
| P1 | Representation dependence | Retained, made explicit | Manuscript continues to define representation as objective input; no claim of intrinsic circuit optimum. |
| P2 | Proposition 2 wording | Addressed | Now `Objective-bound redundancy without cardinality`; explicitly distinguishes objective from polyhedral strengthening. |
| P2 | Experiment mapping | Addressed | E1-E8/SCIP mapping table added to methodology. |
| P2 | Runtime threads | Addressed for revision runners | `benchmark/isolated.py` pins OMP/OPENBLAS/MKL to one thread before numerical imports. Legacy E1 results remain unpinned and are labelled as such. |
| P2 | Joint-QPD context | Partially addressed | Added Ufrecht et al. citation. Schmitt et al. was already cited. Harrow--Lowe, routing-aware, decomposition-aware citations require verified bibliographic metadata before insertion. |

## Certificate Semantics

`Certificate` now records:

- `certificate_kind`: `exact_arithmetic`, `solver_tolerance`, or `verified_conservative`.
- `numerical_safety_margin_log`.
- `conservative_lower_bound_log = LB_reported - margin`.
- `conservative_overhead_factor_bound = exp(UB - LB_reported + margin)`.
- `formal_numerical_proof`.

Branch-and-bound emits `solver_tolerance`, `formal_numerical_proof=false`, and a declared `1e-9` margin. This is transparency, not a proof that `1e-9` bounds all floating-point error. Exact arithmetic Proposition 4 remains valid. A true rigorous numerical certificate still needs dual-feasible recovery plus directed/outward rounding, or rational/interval verification of every lower bound and pruning decision.

## Matched SCIP Capability

`solve_scip_core` supports:

- `g0_basic`, `g1_cardinality`, `g2_b2s` formulations.
- Deterministic SCIP random/permutation seeds.
- Optional validated exact-balanced supplied incumbent.
- Independent equal wall-time checkpoint solves.
- UB, LB, factor, status, node count, LP iterations, SCIP feasibility tolerance, and solver-numerics label.

Full E7: 200 frozen heterogeneous records, five families, n=20--40, ten seeds, independent 2/10/60-s checkpoints. SCIP G0 closes 199/200 at 2 s and 200/200 at 10 s. CERTICUT closes 160/200 at 2 s, 184/200 at 10 s, and 199/200 at 60 s. This rejects custom-solver superiority on the evaluated corpus. See `Phase_12_E7_Frozen_Heterogeneous_Scaling_Report.md`.

Run full E7:

```powershell
& ".venv\Scripts\python.exe" scripts/run_phase12_heterogeneous_scaling.py --sizes 20 24 32 40 --seeds 10 --deadline-s 60 --checkpoints-s 2 10 60
```

Protocol completed; raw evidence frozen. Compare UB, LB, factors, closed rates, time-to-factor thresholds, and raw checkpoint files. Do not use only solved/not-solved.

## Finite-Shot Capability

`validate_finite_shot_comparison` requires exactly two valid exact-balanced plans. It:

- Uses equal total circuit shots per seed.
- Uses shared deterministic QPD/Aer seeds.
- Distributes each plan's budget across its generated fragment experiments.
- Reports each trial estimator, mean, bias, RMSE, standard deviation, QPD overhead, and actual shots.
- Transpiles generated local fragment experiments for Aer compatibility only after QPD sampling.

Smoke E8 witness: `community_matching`, `n=12`, seed `3`.

| Plan | Log objective | Model overhead |
|---|---:|---:|
| Count-optimal | 16.1461 | 10,284,202.81 |
| QPD-optimal | 9.5673 | 14,290.46 |

At 256 total shots/seed, 4 QPD samples/seed, 2 seeds:

| Observable | Count-optimal RMSE | QPD-optimal RMSE |
|---|---:|---:|
| `Z` x 12 | 790.37 | 10.49 |
| `X` + `I` x 11 | 300.05 | 12.62 |

Full E8 is complete: 50 shared seeds, 4096 total shots per plan per seed, and 16 QPD samples. The strong 719.66x reversal improves RMSE for both observables; the moderate 3.27x reversal is mixed with bootstrap intervals crossing zero; the no-reversal control is identical. See `Phase_12_E8_Frozen_Finite_Shot_Report.md`.

Run full E8:

```powershell
& ".venv\Scripts\python.exe" scripts/run_phase12_finite_shot_reversals.py --witnesses 2 --shots 4096 --qpd-samples 16 --trials 20
```

## Changed Files

- `certicut/optimization/certificate.py`
- `certicut/optimization/bnb.py`
- `certicut/optimization/scip_core.py`
- `certicut/qiskit_bridge/operational.py`
- `certicut/benchmark/isolated.py`
- `scripts/run_phase6_6b.py`
- `scripts/run_phase12_heterogeneous_scaling.py`
- `scripts/run_phase12_finite_shot_reversals.py`
- `tests/test_certificate.py`
- `tests/test_final_protocol.py`
- `tests/test_scip_checkpoint.py`
- `tests/test_operational_finite_shots.py`
- `paper/certicut.tex`
- `paper/references.bib`
- `requirements.txt`

## Validation

```text
& ".venv\Scripts\python.exe" -m pytest
121 passed in 22.98s
```

Full E7: 200/200 records. Full E8: 3/3 frozen cases, 50 trials/case. Generated-fragment transpilation handles Aer's unsupported `iswap` instruction.

PDF build blocked:

```text
pdflatex : The term 'pdflatex' is not recognized
```

## Remaining Publication Gates

1. Implement independently verified lower bounds before using `certificate` without `solver-tolerance` qualification.
2. Publish immutable anonymous artifact with raw data, manifests, full configurations, and generator definitions.
3. Revise results around E7's mature-MIP negative result and E8's conditional finite-shot evidence.
4. Install TeX toolchain, rebuild manuscript, inspect bibliography/table overflow, regenerate DOCX only after PDF passes.

## Deliberate Non-Claims

- No custom solver superiority claim.
- No rigorous numerical proof claim.
- No general physical-shot or hardware-cost claim.
- No custom CERTICUT superiority claim; E7 favors SCIP G0 on this corpus.
- No prevalence claim from E5/E6 reversal counts.
