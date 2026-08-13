# CertiCut Phase 10.3 Joint-QPD Cost Validity Report

Ngày: 11/08/2026

## Trạng thái

**PIVOT PASS.** Phase 10.3 rejects the interpretation of the Phase 10.2 operator-Schmidt term as a joint-QPD sampling overhead. A semantic oracle now separates executable independent-QPD cost, non-executable operator-Schmidt surrogate cost, and unimplemented theoretical joint-QPD cost. The closed small-block study gives witnesses in both directions, proving that log operator-Schmidt rank has no universal ordering relative to the executable gatewise independent-QPD cost.

This is a successful scientific outcome. It prevents an invalid joint-QPD claim from entering the paper and establishes the required oracle boundary before further solver or scalability work.

## Research Questions

### RQ-J1: When Is a Temporal-Spatial Block a Legal Joint-Cutting Construction?

**Answer: not merely by grouping.** A temporal-spatial block is an optimizer-side aggregation policy. Overlapping support and bounded layer distance do not provide a QPD decomposition, fragment experiment construction, coefficient list, or reconstruction rule. Therefore a block is marked `joint_qpd` only when an oracle provides all of:

```text
1. a legal decomposition for the selected physical partition,
2. quasiprobability coefficients,
3. a computed sampling overhead,
4. executable fragment/reconstruction semantics.
```

The current repository meets these conditions only for independent two-qubit Qiskit `QPDBasis` decompositions. It does not yet implement the multi-unitary construction of Schmitt, Piveteau, and Sutter, ``Cutting Circuits with Multiple Two-Qubit Unitaries,'' Quantum 9, 1634 (2025), doi:10.22331/q-2025-02-18-1634.

### RQ-J2: What Is the Relation Between Schmidt Surrogate and QPD Overhead?

**Answer: no universal ordering exists relative to gatewise independent QPD.** The current Schmidt value is a structural property of the composed block unitary. Independent QPD cost is the product of QPD overheads assigned to crossed gate occurrences. These are different quantities.

Two witnesses establish the ordering reversal. First, two consecutive CNOT gates on the same endpoints compose to the identity, so their operator-Schmidt rank is one and the surrogate is zero. Gatewise independent cutting still incurs two executable CNOT QPD overheads, giving $\Gamma=9^2=81$ and $\log\Gamma=4.394449$. Thus $J_S<J_{\mathrm{ind}}$. Second, for $RZZ(0.1)$, the generic nonzero rotation has operator-Schmidt rank two, giving $J_S=\log2=0.693147$, while the Qiskit validated independent-QPD cost gives $J_{\mathrm{ind}}=0.364088$. Thus $J_S>J_{\mathrm{ind}}$.

The repeated-CX witness disproves equivalence with gatewise independent-QPD cost. It does not establish any positive or negative relation to the optimal joint-QPD overhead: a legal joint construction could exploit the cancellation. Together, the two witnesses prove only the stated result: the current rank surrogate must not be presented as executable gatewise QPD cost, a generic upper/lower bound for that cost, or the published optimal joint-QPD theorem without an additional theorem and construction.

### RQ-J3: Can the Current Optimizer Claim True Joint-QPD Optimization?

**Answer: no.** Theoretical joint-QPD mode intentionally returns no numeric cost and no decomposition metadata until the published construction is implemented and operationally verified. Phase 10.2's hardware-aware results remain valid as exact optimization of the declared operator-Schmidt-surrogate-plus-hardware objective, not as true joint-QPD results.

## JointCostOracle

The new oracle supports three explicit modes:

| Mode | Returned quantity | Executable | Theorem status |
| --- | --- | --- | --- |
| `independent_qpd` | Product of Qiskit `QPDBasis` overheads for crossed two-qubit gate occurrences | Yes | `exact_independent` |
| `schmidt_surrogate` | $\log\operatorname{rank}_S(B,A)$ for the composed block unitary | No | `surrogate_only` |
| `theoretical_joint_qpd` | No numeric cost until construction exists | No | `unimplemented_theory` |

The oracle fails closed. It never silently replaces an unavailable joint-QPD decomposition by a Schmidt rank, and it never marks a Schmidt estimate as executable.

## Small-Block Study

Ten deterministic blocks and fixed bipartitions were evaluated. Independent cost uses Qiskit Addon Cutting 0.10 `QPDBasis`; the Schmidt term uses SVD on the composed block operator.

| Block | Independent log overhead | Schmidt log surrogate | Difference surrogate - independent |
| --- | ---: | ---: | ---: |
| CX-CX chain, left cut | 2.197225 | 0.693147 | -1.504077 |
| CX-CX chain, right cut | 2.197225 | 0.693147 | -1.504077 |
| iSWAP-iSWAP chain | 3.891820 | 1.386294 | -2.505526 |
| CX-iSWAP chain | 2.197225 | 0.693147 | -1.504077 |
| RZZ(pi/4)-CX chain | 1.762747 | 0.693147 | -1.069600 |
| CZ-RZZ(pi/4) chain | 2.197225 | 0.693147 | -1.504077 |
| Parallel CX blocks | 4.394449 | 1.386294 | -3.008155 |
| Repeated CX on same pair | 4.394449 | 0.000000 | -4.394449 |
| RZZ(0)-CX, one crossed identity-cost gate | 0.000000 | 0.000000 | 0.000000 |
| RZZ(0.1), weak entangling rotation | 0.364088 | 0.693147 | +0.329059 |
| CX-CZ on same pair | 4.394449 | 0.693147 | -3.701302 |

All eleven `independent_qpd` records have executable QPD metadata. All eleven `theoretical_joint_qpd` records correctly return unavailable cost with `unimplemented_theory` status. No point in the study is labeled an executable joint-QPD decomposition.

## Formal Scope

For a block $B$ and physical bipartition $A|\bar A$:

```text
J_ind(B,A) = sum(log(rho_g) for crossed gate occurrences g)
J_S(B,A)   = log(rank_S(U_B; A|Abar))
```

`J_ind` is executable for supported numeric two-qubit Qiskit QPD gates. `J_S` is computed from the total composed unitary and is a structural surrogate. The two values coincide in selected special cases but are not interchangeable.

The Phase 10.2 multi-QPU term is likewise a symmetric aggregation of partition-aware `J_S` values. It remains a stated surrogate objective until an oracle supplies valid multi-QPU joint-QPD semantics.

## Correctness Coverage

| Test | Result |
| --- | --- |
| Independent oracle equals product of crossed Qiskit QPD overheads | PASS |
| Schmidt mode is never executable or decomposition-available | PASS |
| Theoretical mode returns no numeric cost without construction | PASS |
| Existing independent-QPD cost suite | PASS |
| Joint oracle tests after semantic closure | `4 passed in 0.55s` |

## Files

- `certicut/costs/joint_qpd.py`
- `certicut/costs/__init__.py`
- `tests/test_joint_qpd_oracle.py`
- `scripts/run_phase10_3_joint_cost_study.py`
- `results/phase10_3_joint_cost_oracle_study.json`

## Reproduction

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest -q tests\test_joint_qpd_oracle.py tests\test_qpd_costs.py
.\.venv\Scripts\python.exe scripts\run_phase10_3_joint_cost_study.py
```

## Decision

1. Retain `independent_qpd` as the only executable QPD cost in the current CertiCut pipeline.
2. Relabel all Phase 10.2 joint-cost language as `operator-Schmidt surrogate` language.
3. Do not add Benders, larger-K, or new hardware benchmarks until one of the following is achieved:

```text
Strong PASS:
  implement and verify a legal joint-QPD construction for a defined block class.

Pivot PASS:
  retain the hardware-aware Schmidt-surrogate branch as a separate structural co-optimization study,
  while the main CertiCut paper keeps independent QPD as its executable sampling objective.
```

The present result is a **Pivot PASS**. It is more scientifically defensible than extending a cost model with unverified physical semantics. Phase 10.3A closes the ordering claim before theorem-backed oracle implementation begins.

`ponytail:` do not use “joint-QPD cost,” “optimal joint-QPD overhead,” or “executable joint reconstruction” in claims, titles, abstracts, or figure captions for Phase 10.2. Use “operator-Schmidt surrogate” until a decomposition oracle and reconstruction implementation are validated.
