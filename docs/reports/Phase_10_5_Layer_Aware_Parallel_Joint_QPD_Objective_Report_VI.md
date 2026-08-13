# CertiCut Phase 10.5 Layer-Aware Parallel-Joint QPD Objective Report

Ngày: 11/08/2026

## Trạng thái

**STRONG GO.** CertiCut now has an executable theorem-backed objective for legal parallel joint cutting, independently composed across circuit layers. The closed-form objective matches generated Schmitt decompositions on `100/100` random legal parallel layers with maximum log-cost discrepancy `9.77e-15`. An exhaustive balanced-partition search finds a strict six-qubit decision reversal: the independent-QPD optimum is `1.905x` worse than the PJ-QPD optimum when both are evaluated under executable parallel-joint semantics.

This phase formalizes and validates an objective only. It does not yet add PJ-QPD to the certified B2S optimizer.

## Objective Scope

For a fixed circuit dependency layer `l`, every eligible two-qubit gate is pairwise disjoint. Let `C_l(P)` be the crossed gates under partition `P`. For gate `g`, let its KAK coefficient strength be:

```text
s_g = (sum_k |u_g,k|)^2
c_g = log(s_g)
```

For one legal layer, Corollary 4.1 gives:

```text
gamma_l(P) = 2 product_{g in C_l(P)} s_g - 1
Gamma_l(P) = gamma_l(P)^2
```

The empty product is one, so an uncut layer has `gamma_l=1`, `Gamma_l=1`, and zero log cost. When each legal layer is decomposed independently, the execution-policy overhead is:

```text
Gamma_PJ(P) = product_l Gamma_l(P)
J_PJ(P) = 2 sum_l log(2 exp(sum_{g in C_l(P)} c_g) - 1)
```

Equivalently:

```text
J_PJ(P) = sum_l f(t_l)
t_l = sum_{g in layer l} c_g x_g
f(t) = 2 log(2 exp(t) - 1)
```

The name used in this phase is:

```text
parallel-joint independently-composed QPD objective (PJ-QPD)
```

It is not claimed to be a globally optimal temporal joint-QPD cost for the full circuit. It is optimal inside each theorem-eligible parallel layer and independently composed across layers.

## Propositions

### Proposition A: Executable Objective Equivalence

For a fixed legal layer decomposition, `J_PJ(P)=log(Gamma_PJ(P))` equals the overhead of the exact execution policy operationalized in Phase 10.4C.

Reason: each crossed subset in a legal layer is decomposed with theorem coefficient one-norm `gamma_l`; the generated layer overhead is `gamma_l^2`; independently composing layers multiplies overheads and adds log costs.

Validation: `100/100` random legal parallel layers match formula cost to generated-decomposition cost within `1e-10`; observed maximum error is `9.77e-15`.

### Proposition B: Joint Dominance

For every partition within the declared parallel-layer policy:

```text
J_PJ(P) <= J_ind(P)
```

with strict inequality whenever a legal layer has multiple nontrivial crossed two-qubit unitaries in the strict-advantage regime of the theorem. The independent policy is recovered when every crossed layer contains at most one gate.

### Proposition C: Concavity

For:

```text
f(t) = 2 log(2 exp(t)-1)
```

the derivatives are:

```text
f'(t)  = 4 exp(t) / (2 exp(t)-1) > 0
f''(t) = -4 exp(t) / (2 exp(t)-1)^2 < 0
```

Thus PJ-QPD cost is increasing and concave in total crossed KAK strength per layer. The scientific interpretation is an economy of scale: legal cuts co-located in a parallel layer cost less than the same gatewise strengths independently composed in different layers.

## Formula-to-Generated Validation

The validation corpus contains 100 seeded parallel layers of width 2, 4, or 6 with CX, numeric RZZ, and iSWAP gates. Every gate crosses the fixed bipartition. For each layer:

```text
J_formula = J_PJ(P)
J_generated = log(Gamma from generated Lemma 5.2 decomposition)
```

Result:

```text
100/100 match
max |J_formula - J_generated| = 9.77e-15
```

## Decision-Reversal Search

An exhaustive, symmetry-reduced exact-balanced `K=2` search enumerates all partitions with qubit zero fixed to side zero. The deterministic synthetic corpus uses three layers of random perfect matchings over CX, iSWAP, and numeric RZZ gates. Every candidate partition records:

```text
cut gate count
crossed gates by dependency layer
J_independent, Gamma_independent
J_PJ, Gamma_PJ
```

### Strict Six-Qubit Witness

The first strict witness appears at `n=6`, seed `29`, depth `3`.

| Quantity | Independent-optimal partition | PJ-optimal partition |
| --- | ---: | ---: |
| Partition | `(0,1,1,0,0,1)` | `(0,0,1,1,1,0)` |
| Cut gates | 3 | 5 |
| Independent log cost | 9.980865 | 10.543316 |
| Independent overhead | 21609.0 | 37923.1 |
| PJ log cost | 9.980865 | 9.336403 |
| PJ overhead | 21609.0 | 11343.5 |

The independent objective strictly prefers its own partition because:

```text
9.980865 < 10.543316
```

but PJ-QPD strictly prefers the second partition because it co-locates three crossed gates in one legal parallel layer:

```text
9.336403 < 9.980865
```

The independent optimizer's regret under executable PJ semantics is:

```text
R_I_to_PJ = 0.644462
F_I_to_PJ = exp(R_I_to_PJ) = 1.904962
```

This is a strict argmin reversal, not a tie-breaking artifact. The PJ-optimal partition cuts more gates yet has lower executable PJ-QPD overhead.

## Minimal Timing Illustration

For two CNOT cuts:

| Placement of cuts | Gatewise independent overhead | PJ-QPD overhead |
| --- | ---: | ---: |
| same legal parallel layer | 81 | 49 |
| two separate dependency layers | 81 | 81 |

Gatewise independent cost discards layer co-location information. PJ-QPD retains it through the concave layer function.

## Files

- `certicut/optimization/parallel_joint.py`
- `tests/test_parallel_joint_objective.py`
- `scripts/run_phase10_5_formula_validation.py`
- `scripts/run_phase10_5_reversal_search.py`
- `results/phase10_5_formula_generated_validation.json`
- `results/phase10_5_partition_reversal_witness.json`

## Verification

| Check | Result |
| --- | --- |
| two same-layer CX formula gives Gamma=49 | PASS |
| two separated-layer CX formula gives Gamma=81 | PASS |
| increasing concave layer function | PASS |
| formula versus generated decomposition | `100/100`; max error `9.77e-15` |
| strict partition argmin reversal | PASS; factor `1.904962` |
| exact-balanced enumeration symmetry reduction | PASS |

## Decision

**GO for Phase 10.6.** The PJ-QPD objective is executable, differs materially from the independent objective, and changes optimal partition decisions. The next phase may build a small exact pattern-MILP oracle and certificate-safe concavity lower bounds before integrating the objective into an anytime solver.

Freeze the hardware-aware Schmidt-surrogate branch. Ancilla width is metadata of the current Schmitt executor, not an optimization term or universal requirement. Do not open K>2, Benders, or finite-shot experiments before the certificate path is validated.

`ponytail:` permitted claim: “independently composing theorem-optimal parallel joint-QPD decompositions yields a layer-coupled executable objective that can select a different circuit partition than gatewise independent QPD.” Forbidden claim: “globally optimal temporal joint QPD,” “general joint-QPD partitioning,” or “hardware-aware joint-QPD optimization.”
