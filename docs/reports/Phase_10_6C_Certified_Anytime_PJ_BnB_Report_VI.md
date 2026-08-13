# CertiCut Phase 10.6C Certified Anytime PJ-QPD Branch-and-Bound Report

Ngày: 11/08/2026

## Trạng thái

**CORRECTNESS PASS, NO SPECIALIZED-SOLVER ADVANTAGE.** A certificate-safe best-bound branch-and-bound implementation for exact balanced K=2 PJ-QPD partitioning is implemented and validated against the exact pattern-MILP oracle. Geometry and objective cut pools are separated, integral nodes are fathomed only after complete PJ Lovasz separation, and interruption returns valid lower and upper bounds. However, in the matched-time pilot, generic HiGHS pattern MILP proves or improves the tested instances faster at every measured budget. Phase 10.6C does not support a claim that the current specialized PJ solver outperforms generic MILP.

## Solver Architecture

### Immutable Geometry Pool

```text
GeometryCutPool
  exact balanced cardinality
  complete-pair XOR envelope
  B2S metric triangle facets
  immutable after construction
```

### Mutable Objective Pool

```text
ObjectiveCutPool
  globally valid PJ Lovasz epigraph cuts
  key = (layer_id, sorted gate permutation)
  monotonic insertion
  independent version counter
```

Every node stores:

```text
fixed assignments
last completed LP lower bound
LP assignment solution
pj_separation_complete
geometry pool version
PJ objective pool version
```

The LP contains complete-pair cut variables `x_(u,v)` shared across every temporal layer in which that physical pair appears, plus one `eta_l` epigraph variable per layer. Thus the formulation preserves temporal coupling rather than collapsing repeated pairs into an additive interaction weight.

## Separation and Fathoming Semantics

At a node, the solver:

```text
solve LP with current geometry and PJ cut pools
for each layer: sort x_g descending and construct greedy Lovasz cut
add violated globally valid cuts
repeat until no violation or a safe stopping boundary
```

The distinction between incomplete and complete separation is mandatory:

```text
fractional node, incomplete separation:
  valid weaker lower bound; branching remains safe

integral node, incomplete separation:
  do not fathom; add/re-solve PJ cuts first

integral node, complete separation:
  LP objective equals exact PJ objective; incumbent update and fathoming safe
```

Stale node bounds from an older objective pool remain valid lower bounds. Reoptimization when popped is used for strength and integral exactness, not as a prerequisite for certificate correctness.

## Safe Checkpoints

The time limit is checked only after:

```text
a completed LP solve
a completed PJ separation round
both child LP bounds are completed
```

If time expires during separation, the solver preserves the most recent completed LP bound. Missing globally valid PJ cuts can only weaken that bound. The active node is never discarded merely because it was popped from the frontier.

The global certificate at a checkpoint is:

```text
LB = min(UB, min(node LB over frontier and completed active-node state))
LB <= OPT_PJ <= UB
F = exp(UB-LB)
```

## Correctness Ladder

### Exact Oracle Agreement

On 60 deterministic small instances:

```text
n = 4, 6, 8
depth = 2, 3
families = random matching, ring even-odd
seeds = 5
```

the PJ B&B solver proves the same objective as the exact pattern-MILP oracle in all cases:

```text
60/60 exact-oracle matches
```

### Adversarial Regression Cases

| Case | Result |
| --- | --- |
| Mixed CX/RZZ/iSWAP exact objective | PASS |
| Node limit zero: `LB <= OPT <= UB` | PASS |
| Global LB monotone at safe checkpoints | PASS |
| Incumbent UB nonincreasing | PASS |
| Reused logical pair in multiple temporal layers | PASS |
| Incomplete PJ separation, zero round limit | PASS; certificate remains valid |
| Integral node requires complete PJ separation | PASS by solver control flow |

The final regression suite contains:

```text
111 passed in 23.42s
```

## Matched-Time Generic HiGHS Pilot

The generic comparator is the exact layer-pattern MILP solved by HiGHS with the same requested time limit. The SciPy public wrapper exposes incumbent/status but not a generic dual bound, so no generic multiplicative certificate factor is inferred or fabricated.

| Instance | Budget | CertiCut PJ status / factor | Generic HiGHS status / actual time |
| --- | ---: | --- | --- |
| n=8 random depth 3 | 0.05s | time limit / 348227.1 | optimal / 0.011s |
| n=8 random depth 3 | 0.20s | optimal / 1.0 | optimal / 0.009s |
| n=8 random depth 5 | 0.05s | time limit / 1.53e11 | time limit / 0.055s |
| n=8 random depth 5 | 0.20s | time limit / 548643.6 | optimal / 0.181s |
| n=10 random depth 3 | 0.20s | time limit / 353258.5 | optimal / 0.186s |
| n=10 random depth 3 | 1.00s | time limit / 96834.6 | optimal / 0.195s |
| n=10 ring depth 5 | 0.20s | time limit / 209.7 | time limit / 0.208s |
| n=10 ring depth 5 | 1.00s | time limit / 21.1 | optimal / 0.782s |

The specialized solver currently has substantial root/node separation overhead and weak early lower bounds. Generic HiGHS wins every pilot regime in this artifact, either proving first or finding a better incumbent sooner. This is a decision-relevant negative result.

## Files

- `certicut/optimization/pj_bnb.py`
- `certicut/optimization/pj_exact.py`
- `certicut/optimization/pj_lovasz.py`
- `certicut/optimization/pj_lovasz_lp.py`
- `tests/test_pj_bnb.py`
- `tests/test_pj_exact.py`
- `tests/test_pj_lovasz.py`
- `tests/test_pj_lovasz_lp.py`
- `scripts/run_phase10_6c_generic_pilot.py`
- `results/phase10_6c_generic_pilot.json`

## Decision

Freeze Phase 10.6C as a correctness result. Do not position PJ B&B as an algorithmic centerpiece, do not merge it into the main CertiCut paper, and do not continue scaling, Benders, hardware, or finite-shot branches under the current implementation.

The viable publication paths are:

```text
1. Core CertiCut paper:
   independent-QPD certified B2S optimizer; existing evidence chain.

2. Follow-up joint-QPD paper:
   theorem-backed executable PJ-QPD objective, partition reversals, exact oracle,
   and a future solver only if a revised method beats generic MILP in a clear regime.
```

`ponytail:` valid claim: “CertiCut PJ B&B maintains correct anytime certificates on tested exact-oracle instances.” Invalid claim: “CertiCut PJ B&B provides superior early-time certificates or outperforms generic MILP.”
