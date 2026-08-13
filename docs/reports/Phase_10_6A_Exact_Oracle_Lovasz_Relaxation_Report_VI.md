# CertiCut Phase 10.6A Exact PJ Oracle and 10.6B Lovasz Relaxation Report

Ngày: 11/08/2026

## Trạng thái

**PARTIAL ALGORITHMIC PASS.** An independent exact pattern-MILP oracle and a root Lovasz-epigraph lower-bound prototype are implemented for the executable PJ-QPD objective. Pattern MILP matches brute-force exact balanced enumeration on tested small instances. The Lovasz relaxation is valid on the tested oracle instances and is exact at binary layer-cut vertices. A full certified anytime PJ branch-and-bound solver is not implemented in this phase.

## Exact Pattern-MILP Oracle

For each layer `l` with gate set `G_l`, the oracle introduces one binary variable for every crossed-gate pattern:

```text
h_(l,S) in {0,1}, S subseteq G_l
sum_S h_(l,S) = 1
x_g = sum_(S containing g) h_(l,S)
```

The exact objective is:

```text
min sum_l sum_(S subseteq G_l) F_l(S) h_(l,S)
F_l(S) = 2 log(2 exp(sum_(g in S) c_g) - 1)
```

The model retains exact balanced K=2 assignment and XOR cut constraints. Its exponential layer-pattern count makes it an independent small-instance oracle, not a scalable production solver.

## Exact Oracle Validation

The pattern MILP was compared to symmetry-reduced brute-force enumeration on mixed CX/RZZ/iSWAP layered circuits. Both return the same exact PJ objective within tolerance.

| Check | Result |
| --- | --- |
| Pattern MILP versus brute force | PASS |
| Parallel CX layer pattern oracle | PASS |
| Exact balanced symmetry reduction | PASS |

## Submodularity and Lovasz Relaxation

For layer set function:

```text
F_l(S) = f(sum_(g in S)c_g)
f(t) = 2 log(2 exp(t)-1)
```

the gate strengths satisfy `c_g >= 0` and `f` is increasing and strictly concave. Therefore `F_l` is normalized, monotone, submodular. For `S subseteq T` and `g notin T`, the marginal:

```text
f(t_S+c_g)-f(t_S) >= f(t_T+c_g)-f(t_T)
```

decreases with the base set.

At an LP point, sort layer cut values in nonincreasing order `x_(pi_1) >= ... >= x_(pi_m)`. Let:

```text
d_j = F({pi_1,...,pi_j}) - F({pi_1,...,pi_(j-1)})
```

The greedy Lovasz epigraph inequality is:

```text
eta_l >= sum_j d_j x_(pi_j)
```

All such cuts are globally valid. The Lovasz extension equals the PJ layer set cost at every binary gate-cut vector. This preserves the property absent from a chord-only lower bound: after complete separation, an integral node's LP objective equals its true PJ objective and can be safely fathomed.

## Two-CX Example

For two CNOT gates in one layer:

```text
F(empty) = 0
F({1}) = F({2}) = log(9) = 2.197225
F({1,2}) = log(49) = 3.891820
```

For order `x_1 >= x_2`, the greedy cut is:

```text
eta >= 2.197225 x_1 + 1.694596 x_2
```

The reverse permutation gives the symmetric companion cut. Together they are exact at all four binary vertices while defining a convex lower relaxation over the fractional cube.

## Root Prototype Result

On a mixed six-qubit, two-layer CX/RZZ/iSWAP instance:

| Quantity | Value |
| --- | ---: |
| Exact pattern-MILP PJ objective | 3.126001 |
| Lovasz LP lower bound | 2.146213 |
| Greedy epigraph cuts | 2 |
| Separation rounds | 1 |

The lower bound is valid:

```text
2.146213 <= 3.126001
```

The root point is fractional, as expected. No claim is made yet about B2S integration, node-level separation, or proof performance.

## PJ Reversal Prevalence

The systematic small corpus uses exact pattern MILP for:

```text
n = 8, 10, 12
depth = 3, 5
families = random matching; ring even-odd
seeds = 5 per family-size-depth cell
total = 60 instances
```

Results:

| Metric | Value |
| --- | ---: |
| Strict PJ partition reversals | 2 / 60 (3.33%) |
| Maximum regret factor | 1.537515x |
| Mean regret factor | 1.009817x |
| Crafted Phase 10.5 n=6 witness | 1.904962x |

Observed systematic reversals:

| Family | n | Depth | Seed | Regret factor |
| --- | ---: | ---: | ---: | ---: |
| Ring even-odd | 8 | 5 | 4 | 1.051527x |
| Random matching | 10 | 3 | 1 | 1.537515x |

The objective change is therefore not confined to the crafted six-qubit witness, but it is sparse in this first compact corpus. This is a conditional empirical signal, not yet a broad prevalence claim or evidence for merging PJ-QPD into the main paper.

## Correctness Implication for Future B&B

Chord-only layer underestimators remain valid lower bounds but are not exact at binary points; therefore they cannot preserve the old rule:

```text
integral LP solution => fathom node
```

The Lovasz formulation resolves this only after relevant epigraph separation has converged. If interruption occurs during incomplete separation, the restricted LP remains a valid weaker lower bound, so certificate safety is retained. A future B&B implementation must enforce:

```text
solve LP
separate PJ Lovasz cuts until no violation
only then fathom an integral assignment using objective equality
```

## Files

- `certicut/optimization/pj_exact.py`
- `certicut/optimization/pj_lovasz.py`
- `certicut/optimization/pj_lovasz_lp.py`
- `tests/test_pj_exact.py`
- `tests/test_pj_lovasz.py`
- `tests/test_pj_lovasz_lp.py`
- `scripts/run_phase10_6a_prevalence.py`
- `results/phase10_6a_pj_prevalence.json`

## Decision

Advance conditionally to Phase 10.6C: integrate B2S geometry with globally pooled node-separated PJ Lovasz epigraph cuts, then validate certificate invariants against the exact pattern oracle. Run a matched-time generic HiGHS pattern-MILP comparison before claiming an algorithmic advantage.

Do not claim that the present root prototype is an anytime solver or that the reversal effect is prevalent on real circuits. Do not open hardware, finite-shot, K>2, or Benders work.

`ponytail:` current valid claim: “PJ-QPD layer costs are monotone submodular and admit Lovasz epigraph lower cuts exact at binary gate-cut vectors.” Future claim requiring evidence: “CertiCut delivers certified anytime PJ-QPD optimization.”
