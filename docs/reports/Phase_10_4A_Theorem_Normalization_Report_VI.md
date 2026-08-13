# CertiCut Phase 10.4A Theorem-Backed Joint-QPD Normalization Report

Ngày: 11/08/2026

## Trạng thái

**PARTIAL PASS.** A restricted theorem-backed joint-QPD cost oracle is implemented for the exact parallel-gate setting of Schmitt, Piveteau, and Sutter, ``Cutting Circuits with Multiple Two-Qubit Unitaries,'' Quantum 9, 1634 (2025), doi:10.22331/q-2025-02-18-1634, Corollary 4.1. The implementation fixes the normalization between the paper's coefficient one-norm and CertiCut's sampling-overhead convention, validates single-gate reductions against Qiskit QPD costs, and fails closed outside the theorem scope.

The phase is not executable yet. No joint decomposition coefficients, local instrument branches, or reconstruction implementation are generated. Therefore no result from this phase is labeled executable joint QPD.

## Scope

The implemented oracle accepts only:

```text
fixed K=2 bipartition A|B
numeric two-qubit unitary instructions
every instruction has exactly one endpoint in A and one in B
pairwise-disjoint gate supports
parallel multi-unitary cutting setting of Corollary 4.1
```

It rejects:

```text
temporal/spatial grouping by itself
overlapping or repeated gate supports
gates internal to either partition
non-two-qubit instructions
nonunitary instructions
general K>2 or three-party cutting
```

This distinction is architectural: block discovery creates a `BlockCandidate`; theorem applicability independently decides whether that candidate has legal joint-cut semantics.

## Published Convention and CertiCut Adapter

The cited theorem defines the QPD coefficient one-norm:

```text
gamma = sum_r |a_r|
```

Its sampling-shot overhead is `gamma^2`. CertiCut records:

```text
coefficient_l1_norm = gamma
sampling_overhead Gamma = gamma^2
log_sampling_overhead J = log(Gamma) = 2 log(gamma)
```

The conversion is explicit in the oracle. No theorem quantity is inserted directly into the optimizer under a mismatched convention.

## Corollary 4.1 Cost

For pairwise-disjoint two-qubit unitaries $U^{(i)}_{A_iB_i}$ crossing a fixed bipartition, write their KAK coefficients as $u^{(i)}_k$, $k\in\{0,1,2,3\}$. The theorem gives:

```text
gamma_parallel = 2 * product_i (sum_k |u^(i)_k|)^2 - 1
Gamma_parallel = gamma_parallel^2
J_parallel = log(Gamma_parallel)
```

The KAK absolute coefficients are obtained from operator-Schmidt singular values divided by two. This is invariant under local KAK factors and satisfies:

```text
sum_k |u_k|^2 = 1
```

## Applicability Checker

`schmitt_parallel_applicability()` returns:

```text
applicable
theorem_id
fixed physical bipartition
gate instruction indices
reason
```

An ineligible input returns a theorem cost object with every numeric field unavailable. There is no Schmidt fallback and no temporal-block assumption.

## Single-Gate Reduction

The most important normalization gate is that one eligible two-qubit unitary must reproduce CertiCut's existing Qiskit independent-QPD overhead under the shared convention.

| Gate | Theorem `Gamma` | Qiskit `QPDBasis` overhead | Result |
| --- | ---: | ---: | --- |
| CX | 9 | 9 | PASS |
| CZ | 9 | 9 | PASS |
| RZZ(pi/4) | 5.8284271247 | 5.8284271247 | PASS |
| iSWAP | 49 | 49 | PASS |

This gate closes the factor-square risk for the implemented restricted oracle.

## Strict Joint-Advantage Witness

For two parallel, disjoint CNOTs crossing the same fixed bipartition:

```text
per-gate KAK absolute coefficients: (1/sqrt(2), 1/sqrt(2))
gamma_parallel = 7
Gamma_parallel = 49
J_parallel = log(49) = 3.8918202981

gatewise independent overhead = 9^2 = 81
gatewise independent log cost = log(81) = 4.3944491547
```

Thus the theorem-backed parallel cost is strictly lower than independent gatewise cutting for this legal class:

```text
Gamma_parallel < Gamma_independent
49 < 81
```

This is a cost-only theorem validation, not an executable decomposition result.

## Verification

| Check | Result |
| --- | --- |
| CX/CZ/RZZ/iSWAP single-gate reductions | PASS |
| Parallel-CX strict joint advantage | PASS |
| Overlapping temporal chain fail-closed | PASS |
| Theorem normalization plus independent-QPD tests | `14 passed in 3.05s` |

## Files

- `certicut/costs/joint_qpd.py`
- `certicut/costs/__init__.py`
- `tests/test_joint_qpd_oracle.py`

## Decision

Advance only to Phase 10.4B: generate the theorem's local-instrument decomposition and verify that its coefficient norm equals the reported `gamma`. Do not integrate `schmitt_parallel_cost()` into a partition optimizer, label it executable, or extrapolate its exactness beyond pairwise-disjoint parallel two-qubit unitaries.

`ponytail:` Corollary 4.1 proves the implemented scalar cost for its stated parallel setting. It does not legalize temporal-spatial blocks, repeated gates, arbitrary three-qubit hyperedges, K>2 cutting, or a reconstruction implementation that has not been built.
