# E8 Frozen Finite-Shot Equal-Budget Report

Date: 2026-08-12

## Question

Under an equal finite execution budget, does lower modeled independent-QPD overhead correspond to lower empirical estimator error?

Answer: **for the predeclared strong reversal, yes for both observables; for the moderate reversal, results are observable-dependent and the paired bootstrap intervals include zero; the no-reversal control is exactly identical under common seeds.**

This supports a carefully bounded claim: large independent-QPD model-overhead reductions can translate to lower finite-shot error on the evaluated ideal-simulator witness. It does not support a universal finite-shot, hardware, joint-QPD, or noise-aware claim.

## Protocol Integrity

Frozen before full execution:

- Protocol: `results/phase12_e8_protocol_frozen.json`
- Three fixed `n=12` E5 cases:
  - Moderate reversal: `dense_shuffled`, seed `2`, modeled regret factor `3.2671`.
  - Strong reversal: `community_matching`, seed `3`, modeled regret factor `719.6551`.
  - No-reversal control: `ring_even_odd`, seed `0`, modeled regret factor `1`.
- Static exact-balanced logical K=2 gate-cut plans.
- Independent per-gate QPD model, fixed generated instruction representation.
- Qiskit Aer ideal simulator. No hardware topology, routing, noise, or joint-QPD decomposition.
- 50 deterministic shared seeds: `0..49`.
- Each plan receives exactly 4096 circuit shots per seed.
- 16 QPD samples per seed.
- Predeclared observables: `ZZZZZZZZZZZZ`, `XIIIIIIIIIII`.
- Metrics: mean, bias, empirical variance, RMSE, median absolute error, paired bootstrap interval for `RMSE(count)-RMSE(QPD)`.
- Bootstrap: 10,000 paired resamples; seed `20260812`; percentile 95% interval.

Raw validation:

```text
3 prescribed cases; 50 shared seeds; exact 4096 shots per plan per seed;
negative-control partitions and estimator distributions identical.
```

| Evidence | SHA-256 |
|---|---|
| `results/phase12_e8_finite_shot.jsonl` | `F6CBCAF3FA3FA144299120C340EB91B06AF260A2BD84402405C21B3758C8DE33` |
| `results/phase12_e8_finite_shot_summary.json` | `48DB707F2D722EF20BE4FEAC264F4D93D7F1651501CFD83B53A677C5837A7C71` |
| `results/phase12_e8_protocol_frozen.json` | `1AD105530AF08010D71DDFA28C0C682779EBC1743C89FE48640423A11FBEE02D` |

## Plan Costs

| Case | Count-plan log cost | QPD-plan log cost | Count-model overhead | QPD-model overhead | Modeled ratio |
|---|---:|---:|---:|---:|---:|
| Moderate reversal | 28.9631 | 27.7792 | 3.7891e12 | 1.1598e12 | 3.2671x |
| Strong reversal | 16.1461 | 9.5673 | 1.0284e7 | 1.4290e4 | 719.6551x |
| No-reversal control | 6.6679 | 6.6679 | 786.7285 | 786.7285 | 1x |

The quantities above are specified independent-QPD model overheads. They are not end-to-end hardware shot costs.

## Equal-Budget Execution Audit

| Case | Count-plan cut instructions | QPD-plan cut instructions | Actual shots/seed, each plan | Generated fragment experiments |
|---|---:|---:|---:|---|
| Moderate reversal | 13 | 14 | 4096 | Count: 48; QPD: 48 |
| Strong reversal | 6 | 6 | 4096 | Count: 48; QPD: 45 or 48, depending on QPD sampling seed |
| No-reversal control | 4 | 4 | 4096 | 42, 45, or 48; identical between plans for each seed |

Total shots, not shots per generated fragment experiment, are held fixed. The varying generated-experiment count is intrinsic to QPD sample generation and is recorded in raw data.

## Main Results

Positive `RMSE(count)-RMSE(QPD)` favors the QPD-optimal plan. Bootstrap intervals are descriptive for the fixed deterministic seed grid; they are not population-prevalence inference.

### Moderate Reversal

| Observable | Plan | Bias | Variance | RMSE | Median absolute error |
|---|---|---:|---:|---:|---:|
| `ZZZZZZZZZZZZ` | Count-optimal | -7353.16 | 1.5053e9 | 39489.27 | 14844.46 |
| `ZZZZZZZZZZZZ` | QPD-optimal | -12177.49 | 1.9725e9 | 46052.33 | 20283.34 |
| `XIIIIIIIIIII` | Count-optimal | -5393.63 | 5.0902e9 | 71549.41 | 33934.86 |
| `XIIIIIIIIIII` | QPD-optimal | -8382.23 | 3.0087e9 | 55488.05 | 26886.18 |

| Observable | RMSE improvement | Paired bootstrap 95% interval | Interpretation |
|---|---:|---:|---|
| `ZZZZZZZZZZZZ` | -6563.06 | [-24286.03, 8963.31] | Count plan lower observed RMSE; inconclusive interval. |
| `XIIIIIIIIIII` | 16061.36 | [-3035.36, 35078.68] | QPD plan lower observed RMSE; inconclusive interval. |

The moderate witness is deliberately retained as a negative/mixed result. Lower modeled overhead does not yield a directionally consistent finite-shot benefit at this fixed budget across the two predeclared observables.

### Strong Reversal

| Observable | Plan | Bias | Variance | RMSE | Median absolute error |
|---|---|---:|---:|---:|---:|
| `ZZZZZZZZZZZZ` | Count-optimal | -5.43 | 9307.03 | 96.63 | 22.16 |
| `ZZZZZZZZZZZZ` | QPD-optimal | -1.96 | 319.09 | 17.97 | 15.09 |
| `XIIIIIIIIIII` | Count-optimal | -1.94 | 2202.51 | 46.97 | 32.84 |
| `XIIIIIIIIIII` | QPD-optimal | 0.68 | 9.87 | 3.21 | 2.45 |

| Observable | RMSE improvement | Paired bootstrap 95% interval | Interpretation |
|---|---:|---:|---|
| `ZZZZZZZZZZZZ` | 78.66 | [49.85, 103.07] | QPD plan lower RMSE. |
| `XIIIIIIIIIII` | 43.76 | [35.02, 52.30] | QPD plan lower RMSE. |

The QPD-optimal plan reduces observed RMSE by about 5.38x for all-Z and 14.62x for the X observable. This direction is consistent with the 719.66x modeled-overhead ratio, but magnitudes must not be equated: QPD model overhead is not a universal prediction of finite-shot RMSE.

### No-Reversal Control

The two plans have identical partition, cut instructions, modeled cost, generated experiments per seed, estimator distributions, and all reported metrics.

| Observable | RMSE count = QPD | Bootstrap interval |
|---|---:|---:|
| `ZZZZZZZZZZZZ` | 3.6547 | [0, 0] |
| `XIIIIIIIIIII` | 0.5844 | [0, 0] |

This validates the comparison plumbing under common seeds: the pipeline does not mechanically favor the label `QPD-optimal` when plans coincide.

## Interpretation

1. Strong reversal: supports finite-shot practical relevance for one large modeled independent-QPD improvement on ideal simulation.
2. Moderate reversal: rejects any claim that lower modeled QPD overhead always lowers finite-shot error at a fixed budget or for every observable.
3. Control: supports implementation validity, not broad physical relevance.
4. Exact equality of control distributions follows from identical plan plus shared deterministic seeds. It is an implementation control, not an independent stochastic replication.
5. The large absolute errors reveal the intended regime: fixed 4096 shots is far below a stable reconstruction budget for some high-overhead plans. This is evidence about comparative behavior at the frozen equal budget, not a recommendation to execute such plans at that budget.

## Publication-Safe Claim

Use:

> In an equal-total-shot ideal-simulation study with predeclared n=12 witnesses, the QPD-optimal plan lowered RMSE for both observables on a strong 719.66x modeled-overhead reversal. A moderate 3.27x reversal gave mixed, statistically inconclusive results, while a no-reversal control produced identical distributions. Thus modeled independent-QPD overhead can be operationally informative, but does not uniformly determine finite-shot estimator error.

Do not use:

- "QPD-optimal always uses fewer shots."
- "The model factor predicts physical shot savings."
- "Finite-shot validation proves end-to-end hardware benefit."
- "The moderate reversal confirms the model."

## Artifact Commands

```powershell
& ".venv\Scripts\python.exe" scripts/run_phase12_finite_shot_reversals.py --shots 4096 --qpd-samples 16 --trials 50 --output results/phase12_e8_finite_shot.jsonl
& ".venv\Scripts\python.exe" scripts/summarize_phase12_e8.py --input results/phase12_e8_finite_shot.jsonl --output results/phase12_e8_finite_shot_summary.json
```

## Validation

```text
& ".venv\Scripts\python.exe" -m pytest
121 passed in 23.20s
```

## Required Paper Direction

- E8 is a main experiment after E7.
- Report all three cases and both observables.
- Keep moderate mixed result and control in the main table or adjacent text.
- State exact fixed-total-shot semantics, QPD samples, shared seeds, ideal simulator, and no-noise limitation.
- Place finite-shot result after independent-QPD model definition; do not merge RMSE with model-overhead factor semantics.
- E7 remains the principal negative result for custom solver claims; E8 is conditional operational evidence, not a replacement for model scope limits.
