# CertiCut Phase 4 Strong Branching Report

Ngày: 11/08/2026

## Trạng thái

PASS correctness. **NO-GO for GNN in current B2S-R + H2 regime.** Strong branching is substantially more expensive but does not materially reduce the observed search tree on the first hard expert corpus.

## Fixed Baseline

```text
LP: B2S-R frozen root cut pool
warm start: H2
node selection: best-bound
capacity: exact balanced K=2
branch baseline: most-fractional
node separation: off
```

## Branching Variants

```text
MF:      zero probe LPs
SB-4:    top 4 fractional candidates
SB-8:    top 8 fractional candidates
SB-Full: every branchable fractional qubit
```

Score:

```text
Delta0 = LB(z_i=0) - LB(node)
Delta1 = LB(z_i=1) - LB(node)
SB(i) = 0.9 * min(Delta0, Delta1) + 0.1 * max(Delta0, Delta1)
```

All probes use the same frozen B2S-R root pool as the actual node. The two child LP results for the selected variable are cached/reused; unselected probes are logged as expert overhead. `q0` is excluded because symmetry fixes it to fragment 0.

## Correctness

- SB completion equals Phase 2 MILP optimum on `100/100` seeded small instances.
- SB node-limit certificate remains `LB <= OPT <= UB`.
- Structural result and SB labels deterministic; timing intentionally excluded from equality check.
- Full SB score vectors are stored, not only winning labels.
- Full suite: `44 passed`.

## Structural Experiment

First expert corpus: `6` B2S-R fractional hard roots at `n=26`, H2, `node_limit=30`. The initial `n=26,32` full-SB matrix was stopped because dense full probing exceeded practical runtime; n=26 is the controlled first rung for the scientific decision.

| Metric | MF | SB-4 | SB-8 | SB-Full |
| --- | ---: | ---: | ---: | ---: |
| Optimal | `6/6` | `6/6` | `6/6` | `6/6` |
| Median nodes | `4` | `4.5` | `4.5` | `4.5` |
| p90 nodes | `7` | `7` | `7` | `6` |
| Max nodes | `13` | `11` | `9` | `15` |
| Median total time | `0.852s` | `2.082s` | `3.909s` | `12.674s` |
| p90 total time | `0.969s` | `2.302s` | `4.972s` | `17.217s` |
| Median probe LP solves | `0` | `20` | `48` | `146` |
| Median SB probe time | `0s` | `1.635s` | `3.617s` | `12.330s` |

Selected-child caching works: strong branching's normal child LP time is effectively absent in this profile; runtime increase is attributable to unselected probe evaluation, not duplicate solves.

## Decision

```text
MF versus SB tree reduction: negligible on first hard expert corpus.
SB cost: large and monotonic with candidate set size.
SB-Full: not a practical expert under current LP cost.
```

The GO criterion for learning is not met:

```text
p90 nodes SB-Full = 6
p90 nodes MF      = 7
```

This does not justify a learned imitation policy. Current priority should be external baselines and certified polyhedral optimizer evaluation, not GNN.

## Labels

`results/strong_branching_states.jsonl` contains `63` full-score SB states:

```text
instance_id
node_depth
current_lb
fractional_variables
candidate_scores
selected_variable
probe_time_s
```

These are retained as research artifacts. If a future larger hard corpus shows SB tree reductions, labels support ranking/top-k imitation rather than brittle single-class labels.

## Files

- `certicut/optimization/bnb.py`: strong branching score, selected-probe cache, SB metrics/state export.
- `tests/test_strong_branching.py`: oracle, timeout, structural determinism tests.
- `scripts/run_phase4.py`: MF/SB-4/SB-8/SB-Full structural experiment.
- `results/phase4_records.jsonl`
- `results/phase4_summary.json`
- `results/strong_branching_states.jsonl`

## Verification

```text
44 passed in 21.23s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase4.py
```

`ponytail:` SB-Full was profiled only at n=26 because probe cost grows rapidly; do not use this narrow result to claim SB never helps at scale, but it is sufficient to block GNN implementation for V1 until contrary tail evidence exists.
