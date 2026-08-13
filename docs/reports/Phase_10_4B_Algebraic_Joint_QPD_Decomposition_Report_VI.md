# CertiCut Phase 10.4B Algebraic Theorem-Backed Parallel Joint-QPD Decomposition Report

Ngày: 11/08/2026

## Trạng thái

**DECOMPOSITION PASS, OPERATIONAL VALIDATION PENDING.** The restricted Schmitt--Piveteau--Sutter parallel two-qubit-unitary construction is implemented algebraically according to Lemma 5.2 and Corollary 4.1 of ``Cutting Circuits with Multiple Two-Qubit Unitaries,'' Quantum 9, 1634 (2025), doi:10.22331/q-2025-02-18-1634. Full complex Weyl/KAK data, relative phases, signed local instruments, outer real QPD coefficients, coefficient one-norm, and channel reconstruction are verified for the supported exact class.

No ancilla circuit realization, sampled execution, or observable reconstruction has been generated. Every returned decomposition remains `operationally_executable=false` until Phase 10.4C.

## Exact Scope

The implementation accepts only a verified tensor-product parallel block:

```text
K=2 fixed physical bipartition A|B
numeric two-qubit unitary instructions
one endpoint on A and one endpoint on B for every gate
pairwise-disjoint supports
all selected gates share one circuit layer
selected instruction interval contains no interleaved operation
```

The checker records:

```text
parallel_tensor_product_verified = true
```

Temporal-spatial proximity does not imply eligibility. Repeated gates, overlapping chains, gates in different layers, internal gates, and interleaved local operations fail closed. The separate black-box/interleaved theorem setting is not implemented in this phase.

## Full KAK Representation

Phase 10.4A used only operator-Schmidt magnitudes to evaluate a scalar theorem cost. Phase 10.4B uses Qiskit `TwoQubitWeylDecomposition` to recover full complex data. For each supported gate, the implementation obtains:

```text
u_k = |u_k| exp(i phi_k)
local pre-A, pre-B, post-A, post-B factors
Weyl central coefficients and global phase
```

Before any joint construction, the reconstructed two-qubit unitary is compared to the input modulo global phase:

```text
min_alpha ||U - exp(i alpha) U_KAK||_F < 1e-12
```

The assembled tensor-product KAK unitary is then compared independently to the selected parallel circuit unitary in ordered `A_1,...,A_n,B_1,...,B_n` basis. This catches tensor-order and local-factor orientation errors that scalar norm checks cannot reveal.

## Lemma 5.2 Construction

For each gate KAK decomposition, the implementation forms composite terms:

```text
w_k = product_i u^(i)_(k_i)
L_k = tensor_i sigma_(k_i)
R_k = tensor_i sigma_(k_i)
```

For every nonzero composite coefficient, it creates a diagonal QPD term:

```text
outer coefficient = |w_k|^2
local maps = Ad(L_k) on A, Ad(R_k) on B
ancillas = 0 per side
```

For every unordered pair `k<k'`, it creates two interference terms with:

```text
theta = (arg(w_k) - arg(w_k')) / 2
outer coefficients = +2|w_k||w_k'| and -2|w_k||w_k'|
```

Each local signed instrument is represented by its two CP branches:

```text
l_plus  = (L_k + exp(-i theta)L_k') / 2
l_minus = (L_k - exp(-i theta)L_k') / 2
C = C_plus - C_minus
```

and analogously on B. The outer coefficient remains real. Complex KAK phases are carried by local branch operators; they are not emitted as complex quasiprobabilities.

## Sampling Hierarchy and Ancillas

The construction uses the theorem's signed-instrument semantics:

```text
sample outer term t using |a_t| / gamma
execute one local CP branch on A and one on B
postprocess sign(a_t) * branch_sign_A * branch_sign_B
```

Branch outcomes are not flattened into independent outer QPD terms. Doing so would incorrectly inflate the coefficient one-norm.

Metadata records the width requirement:

| Term type | Ancillas on A | Ancillas on B |
| --- | ---: | ---: |
| diagonal | 0 | 0 |
| interference | 1 | 1 |

These ancillas are not yet included in optimizer capacity accounting. That integration remains deferred until operational circuit construction exists.

## Algebraic Acceptance Checks

For every eligible block, the implementation checks:

```text
1. individual KAK reconstruction modulo global phase
2. composite parallel KAK reconstruction modulo global phase
3. number of outer QPD terms = N^2, for N nonzero composite coefficients
4. sum_t |a_t| = gamma_theorem
5. Gamma = gamma^2 and J = 2 log(gamma)
6. every C_plus/C_minus and D_plus/D_minus branch is CP by construction
7. C_plus + C_minus and D_plus + D_minus are trace preserving within 1e-10
8. exact algebraic channel reconstruction for blocks with at most two parallel gates
9. unsupported candidate returns unavailable rather than a surrogate
```

The channel reconstruction is built branchwise from `A_branch tensor B_branch`, avoiding a vectorization-order assumption when composing local superoperators.

## Term-Count and Norm Witnesses

| Block | N composite terms | Outer terms | gamma | Gamma | Algebraic channel error |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 CX | 2 | 4 | 3 | 9 | `1.92e-15` |
| 1 CZ | 2 | 4 | 3 | 9 | `1.31e-15` |
| 1 RZZ(pi/4) | 2 | 4 | 2.414214 | 5.828427 | `3.33e-16` |
| 1 iSWAP | 4 | 16 | 7 | 49 | `6.19e-16` |
| 2 parallel CX | 4 | 16 | 7 | 49 | `4.61e-15` |
| 3 parallel CX | 8 | 64 | 15 | 225 | not materialized |
| 2 parallel iSWAP | 16 | 256 | 31 | 961 | `1.93e-15` |
| parallel CX + RZZ(pi/4) | 4 | 16 | 5.828427 | 33.970563 | `1.19e-14` |
| 2 parallel RZZ(0.1) | 4 | 16 | 1.419267 | 2.014319 | `2.31e-15` |

For the three-parallel-CX case, the complete six-qubit superoperator is intentionally not materialized. Its composite KAK unitary reconstruction error is `8.74e-15`; the `N^2=64` construction and theorem norm pass. Full channel reconstruction is exercised for all supported micro-corpus blocks with one or two parallel gates.

## Strict Joint Advantage

The decomposition reproduces the theorem advantage:

```text
2 parallel CX:
Gamma_joint = 49
Gamma_independent = 81

2 parallel iSWAP:
Gamma_joint = 961
Gamma_independent = 2401
```

The result is theorem-backed for the exact parallel class. It is not yet an operational fragment experiment result.

## Invariance

Global-phase invariance is tested by replacing CX with `exp(i*0.371) CX`. The decomposition preserves `gamma`, `Gamma`, and reconstructed channel semantics. Tests assert semantic quantities rather than raw KAK term ordering, which can vary under Weyl/KAK gauge choices.

## Micro-Corpus

The persisted study contains nine legal parallel blocks and one deliberately illegal temporal-overlap block:

```text
single CX, CZ, RZZ(pi/4), iSWAP
two and three parallel CX
two parallel iSWAP
parallel mixed CX/RZZ
parallel weak RZZ(0.1)
illegal overlapping temporal CX chain
```

All legal cases have `parallel_tensor_product_verified=true`. The illegal chain returns no decomposition because the selected gates do not occupy one common circuit layer.

## Verification

| Check | Result |
| --- | --- |
| Full complex Weyl/KAK reconstruction | PASS |
| Composite parallel KAK reconstruction | PASS |
| `N^2` outer-term construction | PASS |
| Theorem coefficient one-norm and Gamma | PASS |
| CP branch and CPTP branch-sum checks | PASS |
| Algebraic channel reconstruction, <=2 parallel gates | PASS |
| Global phase invariance | PASS |
| Illegal temporal overlap fails closed | PASS |
| Joint oracle/decomposition tests | `12 passed in 1.95s` |
| Full repository regression | `91 passed in 22.89s` |

## Files

- `certicut/costs/joint_parallel.py`
- `certicut/costs/joint_qpd.py`
- `certicut/costs/__init__.py`
- `tests/test_joint_qpd_oracle.py`
- `scripts/run_phase10_4b_decomposition_study.py`
- `results/phase10_4b_parallel_decomposition_study.json`

## Decision

Advance to Phase 10.4C only: map the algebraic CP branches to the theorem's local ancilla instruments, generate exact subexperiments, and verify observable reconstruction against uncut statevectors. Maintain:

```text
operationally_executable = false
```

until predicted overhead equals generated-decomposition overhead and exact reconstruction error is below `1e-10`.

`ponytail:` this phase validates the published algebraic decomposition in the restricted parallel K=2 setting. It does not validate hardware execution, finite-shot behavior, arbitrary temporal blocks, interleaved black-box maps, general K, or optimizer integration.
