# CertiCut Phase 11.2 Contribution-Isolation and Novelty Audit Report

Ngày: 11/08/2026

## Trạng thái

**MIXED PASS.** Solver-agnostic root analysis observes strict empirical complementarity between balanced cut cardinality and metric triangles on the completed circuit-derived audit: neither family improves the complete-pair B0 root bound alone, whereas their combination closes half of root instances and reduces the median log gap by two orders of magnitude. This is empirical polyhedral insight, not a general complementarity theorem. However, Phase 11.1 showed that static B2S materialization does not help mature SCIP production performance on the hard-90 pilot. A small exact PJ-QPD audit finds one material real-QAOA partition reversal but is too small for a main-paper pivot.

## Novelty Audit

### Established Machinery: Do Not Claim as New

```text
weighted minimum bisection
branch-and-bound
primal/dual MIP bounds
metric triangle inequalities
cut-polytope facets
generic MIP anytime certificates
```

### Application-Specific Contributions: Defensible

```text
independent-QPD log-overhead circuit-to-bisection mapping
multiplicative sampling interpretation F = exp(UB-LB)
safe-stop certificate semantics for circuit-cut plans
representation sensitivity under actual QPD gate costs
operational independent-QPD reconstruction validation
```

### Empirically Supported Polyhedral Result

```text
balanced cardinality and metric triangles are complementary under the
complete-pair root relaxation; B2S is not merely either component alone.
```

The result does not establish that a custom B&B engine outperforms mature MIP solvers.

## 11.2A Root Polyhedral Decomposition

All four variants use the same complete-pair `z/x` representation, exact balance, fixed label symmetry, tolerance, and LP backend:

| Variant | Added family |
| --- | --- |
| B0 | complete-pair XOR/balance only |
| C | B0 plus balanced cut cardinality |
| T | B0 plus dynamically separated metric triangles |
| CT | B0 plus cardinality and dynamically separated triangles |

The completed audit uses 24 circuit-derived records:

```text
families: random, dense, weighted-random, noisy-community
sizes: n=16,24
seeds: 0,1,2
```

The intended n=32/40 all-violated separation rung exceeded a 10-minute audit budget before one complete matrix could be produced. It is not reported as a completed result. This exposes an engineering limitation of unrestricted all-violated root triangle closure, not a validity failure.

### Root Results

| Formulation | Root exact | Median log gap | p90 log gap | Median LP time | Median active triangles |
| --- | ---: | ---: | ---: | ---: | ---: |
| B0 | 0 / 24 | 26.2935 | 52.4468 | 0.3211s | 0 |
| C | 0 / 24 | 26.2935 | 52.4468 | 0.3429s | 0 |
| T | 0 / 24 | 26.2935 | 52.4468 | 0.2832s | 0 |
| CT (B2S) | 12 / 24 | 0.2848 | 3.8761 | 2.3222s | 947 |

Across all 24 records:

```text
C root LB equals B0 root LB: 24/24
T root LB equals B0 root LB: 24/24
CT root LB strictly dominates B0: 24/24
```

The correct conclusion is a strict synergy:

```text
cardinality alone can be satisfied by fractional/zero-cost complete-pair structure
triangles alone do not force the balanced cut mass into weighted interactions
the combination couples global balanced cut mass to metric geometry
```

This explains the prior B2S package result more precisely than saying B2S ``dominates.''

## Relation to Phase 11.1 SCIP Audit

The hard-90 SCIP pilot found:

| Method | Proven / 90 | Median wall-clock |
| --- | ---: | ---: |
| SCIP basic XOR/balance | 90 | 0.0640s |
| CertiCut B2S-R + H2 | 90 | 0.0692s |
| SCIP + static cardinality | 81 | 0.3373s |
| SCIP + static all B2S | 76 | 0.1020s |

The two results are consistent. The root LP study shows B2S polyhedral strength; the SCIP study shows that fully materializing the same geometry is not an economical production strategy within mature SCIP on the audited pilot. Root separation and static materialization are different computational policies.

No SCIP root-separator plugin, controlled-SCIP mode, H2 MIP start injection, or full E1 matched-checkpoint audit was completed in this phase. Those remain explicit gaps rather than inferred results.

## 11.2-PJ Real-Circuit Relevance Audit

The exact PJ pattern oracle was used on deterministic MQT Bench algorithm-level circuits at `n=8,12`. QAOA parameters were bound to `pi/4`; VQE/BV are evaluated after deterministic CX normalization. This is a six-record relevance screen, not a prevalence study.

| Family | n | Strict reversal | PJ regret of independent optimum |
| --- | ---: | --- | ---: |
| QAOA, bound pi/4 | 8 | Yes | 2.732611x |
| QAOA, bound pi/4 | 12 | No | 1.0x |
| VQE Real-Amplitudes | 8 | No | 1.0x |
| VQE Real-Amplitudes | 12 | No | 1.0x |
| BV | 8 | No | 1.0x |
| BV | 12 | No | 1.0x |

The QAOA n=8 case is material:

```text
J_PJ(P_independent) = 25.864066
J_PJ(P_PJ)          = 24.858808
F_independent_to_PJ = 2.732611
```

This confirms that the executable PJ-QPD objective can change a real benchmark partition, not merely a crafted synthetic instance. The evidence is one strict case in six and therefore insufficient to claim common real-circuit prevalence or to pivot the main paper without expansion.

## Publication Decision

### Core CertiCut

Keep the core paper backend-neutral:

```text
QPD-aware certifiable circuit-cut formulation
root-separated complementary polyhedral strengthening
direct multiplicative interpretation of global optimization bounds
representation-sensitive and operational evidence
```

Do not state or imply custom B&B superiority over generic SCIP.

### PJ-QPD Branch

Keep as a follow-up candidate:

```text
theorem-backed executable parallel joint-QPD construction
layer-coupled objective
synthetic strict reversal
one material real-QAOA reversal
exact pattern oracle
```

Do not merge PJ-QPD into the main paper yet. The branch requires a larger real-circuit relevance audit or a SCIP-plus-Lovasz layer-width crossover result before it can carry a central publication claim.

## Files

- `certicut/optimization/core_root_lp.py`
- `tests/test_core_root_lp.py`
- `scripts/run_phase11_2_root_decomposition.py`
- `results/phase11_2_root_tail.json`
- `scripts/run_phase11_2_pj_real_audit.py`
- `results/phase11_2_pj_real_audit.json`

## Verification

```text
Phase 11.2 module tests: 2 passed
Full repository regression: 113 passed in 40.76s
```

## Next Decision

Stop feature research pending manuscript positioning. A concise next audit, only if needed for a top-tier optimization claim, is a selected-cut SCIP separator study on the n=32/40 tail. Otherwise freeze the core evidence, revise manuscript novelty wording, and retain PJ-QPD as a follow-up branch.

`ponytail:` valid claim: “Cardinality and triangle inequalities exhibit strong root-bound complementarity under CertiCut's complete-pair relaxation.” Invalid claim: “Either component alone explains B2S,” “B2S statically improves SCIP,” “PJ-QPD reversals are prevalent on real circuits,” or “custom CertiCut search outperforms SCIP.”
