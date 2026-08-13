# CertiCut Phase 10.4C Operational Parallel Joint-QPD Reconstruction Report

Ngày: 11/08/2026

## Trạng thái

**FULL OPERATIONAL PASS.** The theorem-backed restricted parallel joint-QPD construction now has executable ancilla-instrument semantics under exact branch enumeration. For every operational micro-corpus block, the generated outer coefficient norm equals the theorem coefficient one-norm, the generated sampling overhead equals `gamma^2`, and reconstructed Pauli-product expectations agree with the exact uncut channel to below `1e-10`.

This status is limited to exact simulation of legal parallel K=2 blocks with product input states across A|B. It is not a finite-shot, noisy-Aer, FakeBrisbane, live-hardware, arbitrary-temporal-block, globally entangled input, or optimizer result.

## Exact Operational Scope

```text
K = 2 fixed bipartition
one verified tensor-product parallel cross-partition layer
pairwise-disjoint numeric two-qubit unitaries
exact branch enumeration
arbitrary product input density matrices rho_A tensor rho_B and local Pauli-product observables
no finite-shot sampling
no hardware execution
no optimizer integration
```

The theorem applicability checker remains unchanged from Phase 10.4B. A temporal block becomes executable only after it independently passes common-layer, contiguous-region, disjoint-support, and fixed-bipartition checks.

## Dedicated Joint Bridge

The operational implementation is separate from Qiskit Addon Cutting `QPDBasis` because a parallel joint decomposition consists of correlated outer QPD terms and signed local instruments. The bridge uses Qiskit only for direct circuit/unitary construction of the ancilla multiplexor; it does not force the construction into the independent-gate QPD API.

```text
certicut/qiskit_bridge/joint_parallel.py
```

Exact reconstruction is a distinct API from a future sampler. It enumerates outer terms with their real outer coefficients directly and never mixes exact coefficients with sampling probabilities `|a_t|/gamma`.

## Ancilla Interference Instrument

For a theorem interference instrument with branch Kraus operators $K_+$ and $K_-$, the bridge constructs:

```text
ancilla |0>
    H
    M = |0><0| tensor (K+ + K-) + |1><1| tensor (K+ - K-)
    H
    measure ancilla
```

The controlled relative phase is retained inside the branch operators before building `M`; it is never discarded as a global phase. The conditional Kraus operators satisfy:

```text
<0| H M H |0> = K+
<1| H M H |0> = K-
```

For a CNOT interference witness, conditional-Kraus errors are:

| Side | `||K_0-K_+||_F` | `||K_1-K_-||_F` |
| --- | ---: | ---: |
| A | `2.60e-16` | `2.60e-16` |
| B | `1.92e-16` | `1.92e-16` |

This bridge-level gate prevents hidden relative-phase errors from being masked by scalar norm or term-count checks.

## Exact Reconstruction Rule

For each outer term $t$ with real coefficient $a_t$, the exact local signed expectations are evaluated over the instrument branches:

```text
m_A(t) = sum_a sign_A(a) Tr[O_A K_A,a rho_A K_A,a dagger]
m_B(t) = sum_b sign_B(b) Tr[O_B K_B,b rho_B K_B,b dagger]
```

The reconstructed expectation is:

```text
<O>_joint = sum_t a_t m_A(t) m_B(t)
```

No outer coefficient is normalized by `|a_t|/gamma` in this exact-enumeration mode. The generated overhead is recomputed independently from the generated outer terms:

```text
gamma_generated = sum_t |a_t|
Gamma_generated = gamma_generated^2
```

Ancilla outcomes are instrument outcomes that contribute signed postprocessing. They are not flattened into additional outer QPD coefficients.

## Operational Micro-Corpus

Each legal case is evaluated against six deterministic Pauli-product observables containing X, Y, Z, and mixed-axis products. Inputs are nontrivial local density matrices. The final case uses a locally dressed numeric CNOT, exercising full KAK local pre/post orientation.

| Block | Outer terms | Gamma theorem/generated | Max observable error | Required width A/B |
| --- | ---: | ---: | ---: | --- |
| single CX | 4 | 9 / 9 | `6.67e-16` | 2 / 2 |
| single RZZ(pi/4) | 4 | 5.828427 / 5.828427 | `1.11e-16` | 2 / 2 |
| single iSWAP | 16 | 49 / 49 | `5.60e-17` | 2 / 2 |
| 2 parallel CX | 16 | 49 / 49 | `1.39e-16` | 3 / 3 |
| parallel CX + RZZ(pi/4) | 16 | 33.970563 / 33.970563 | `3.10e-17` | 3 / 3 |
| 2 parallel iSWAP | 256 | 961 / 961 | `1.12e-16` | 3 / 3 |
| 2 parallel RZZ(0.1) | 16 | 2.014319 / 2.014319 | `0.00e+00` | 3 / 3 |
| locally dressed CX | 4 | 9 / 9 | `2.52e-16` | 2 / 2 |

All eight cases satisfy:

```text
|gamma_generated - gamma_theorem| < 1e-12
|Gamma_generated - Gamma_theorem| < 1e-12
max_O |<O>_joint - <O>_uncut| < 1e-10
```

The maximum observed reconstruction error across the complete corpus is:

```text
6.666141806797044e-16
```

## Headline Parallel Witness

For two disjoint CNOTs in one legal parallel layer:

```text
gamma_generated = 7
Gamma_generated = 49
Gamma_independent = 9^2 = 81
max reconstruction error = 1.39e-16
```

The result verifies both the theorem-predicted joint advantage and executable exact reconstruction. Two parallel iSWAP gates provide the phase-rich stress witness:

```text
outer terms = 256
Gamma_generated = 961
Gamma_independent = 49^2 = 2401
max reconstruction error = 1.12e-16
```

## Ancilla Capacity Semantics

The bridge exposes required fragment width before execution:

| Term class | Data qubits per side | Extra ancilla per side |
| --- | ---: | ---: |
| one cut-gate block with interference | 1 | 1 |
| two parallel cut-gate block with interference | 2 | 1 |

If an available fragment width cannot accommodate the required local ancilla, the bridge returns:

```text
operationally_executable = false
reason = ancilla_capacity
```

This semantic check passes. The listed width is a requirement of the current Schmitt-based bridge, not a universal requirement of optimal parallel joint cutting; other legal executor constructions can have different ancilla tradeoffs. Ancilla width is not yet part of the partition optimizer's feasibility model.

## Verification

| Check | Result |
| --- | --- |
| Conditional ancilla Kraus operators match theorem branches | PASS |
| Generated gamma equals theorem gamma | PASS, 8/8 |
| Generated Gamma equals theorem Gamma | PASS, 8/8 |
| Multiple Pauli-product reconstructions | PASS, 8/8 |
| 2 parallel CX realizes Gamma=49 | PASS |
| Mixed CX/RZZ, iSWAP, weak rotation, local dressing | PASS |
| Ancilla capacity failure is explicit | PASS |
| Illegal temporal block remains fail-closed | inherited PASS |
| Joint oracle/bridge tests | `16 passed in 2.06s` |
| Full repository regression | `96 passed in 24.01s` |

## Files

- `certicut/qiskit_bridge/__init__.py`
- `certicut/qiskit_bridge/joint_parallel.py`
- `tests/test_joint_qpd_oracle.py`
- `scripts/run_phase10_4c_operational_study.py`
- `results/phase10_4c_operational_joint_reconstruction.json`

## Decision

Phase 10.4C completes the theorem-backed executable parallel joint-QPD oracle for its restricted class. Phase 10.5 may now study whether layer-aware legal parallel joint costs change optimal circuit-partition decisions relative to gatewise independent QPD.

Do not yet reconnect the hardware-aware Phase 10.2 optimizer. First formulate and validate a layer-aware joint objective whose scope is exactly: optimal joint QPD inside each legal parallel layer, independently composed across layers.

`ponytail:` permitted wording: “theorem-backed parallel joint-QPD decomposition with exact operational reconstruction under branch enumeration.” Forbidden wording: “finite-shot validated,” “noise-resilient,” “hardware executed,” “global temporal joint-QPD optimum,” or “general K joint cutting.”
