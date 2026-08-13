# E12: Representation-Induced Optimal-Placement Regret -- Experiment Report

**Date:** 2026-08-13
**Experiment ID:** E12 (v2 -- tie-safe corrected)
**Script:** `scripts/run_e12_representation_placement_regret.py`
**Results:** `results/e12_representation_placement_regret.json`

---

## 1. Research Question

Paper hien tai (CertiCut) da chung minh rang circuit representation anh huong den *absolute independent-QPD cost*: cung mot logical circuit, CX-normalized representation co the cho `J*_CX` lon hon `J*_native` nhieu bac.

Tuy nhien cau hoi manh hon chua duoc tra loi:

> **Neu optimizer chon partition toi uu dua tren representation A, partition do co con toi uu khi circuit duoc danh gia duoi representation B khong?**

Hai cau hoi hoan toan khac nhau. Co the `J*_A >> J*_B` nhung cung mot partition van optimal cho ca A va B.

E12 kiem tra dieu do thong qua **tie-safe cross-representation placement regret**.

---

## 2. Metrics

### 2.1 Placement Regret

Cho cung mot logical circuit voi hai representation a, b. Moi representation tao ra interaction weights `w^(a)_{ij}`, `w^(b)_{ij}`. Voi partition P:

```
J_a(P) = sum_{i<j} w^(a)_{ij} * 1[f(i) != f(j)]
```

**Tie-safe cross-representation regret:**

```
Delta_{a->b} = min_{P in argmin J_a} J_b(P) - J_b*
R_{a->b} = exp(Delta_{a->b})
```

- `R = 1`: ton tai it nhat mot partition toi uu duoi representation a cung toi uu duoi b.
- `R > 1`: moi partition toi uu duoi a deu suboptimal khi danh gia duoi b.

### 2.2 Optimality Margin

```
m_a = min_{P not in argmin J_a} [J_a(P) - J_a*]
```

### 2.3 Stability Diagnostic

```
kappa_{a->b} = ||w^(b) - w^(a)||_1 / m_a
```

### 2.4 Representation-Regret Upper Bound (Proposition)

```
R_{a->b} <= exp(||w^(b) - w^(a)||_1)
```

### 2.5 Stability Theorem

```
m_a > ||w^(b) - w^(a)||_1  =>  R_{a->b} = 1
```

Tuong duong: `kappa_{a->b} < 1 => R_{a->b} = 1`.

Stronger form:

```
m_a > ||delta||_1  =>  argmin J_b  subset  argmin J_a
```

### 2.6 Corollary: Positive-Scaling Invariance

Neu `w^(b) = c * w^(a)` voi `c > 0`, thi `argmin J_a = argmin J_b` va `R_{a->b} = R_{b->a} = 1`.

---

## 3. Experiment Design

### 3.1 Protocol

- **Cung source circuit** cho ca hai representation (verified bang `source_fingerprint`)
- **CX-normalized** (a): `transpile(logical, basis_gates=["rz","sx","x","cx"], coupling_map=None, optimization_level=1, seed_transpiler=0)`
- **Native-QPD** (b): recursive decomposition giu nguyen native 2-qubit gates (`rzz`, `cp`, `swap`, `cz`, `crz`...)
- **Khong hardware routing**: `coupling_map=None` cho ca hai. Dam bao do thuan representation effect, khong lan routing + topology.
- **Unitary equivalence verified**: `U_A = e^{i*phi} * U_source`, `U_B = e^{i*phi} * U_source` -- max deviation < 1e-13 cho moi instance kiem tra duoc.

### 3.2 Tiers

| Tier | Method | K values | n range | Tie-safe |
|------|--------|----------|---------|----------|
| Exact | Exhaustive enumeration | 2, 3 | 4--10 | Yes (full argmin set) |
| SCIP tie-safe | Two-stage lexicographic MIP | 2, 3 | 12--16 | Yes (solver-tolerance) |

**SCIP tie-safe protocol (v2):**

Stage 1: Solve `J*_a = min_P J_a(P)` and `J*_b = min_P J_b(P)` independently.

Stage 2a: Solve `C_{a->b} = min_P J_b(P)  s.t.  J_a(P) <= J*_a + tau_opt`.

Stage 2b: Solve `C_{b->a} = min_P J_a(P)  s.t.  J_b(P) <= J*_b + tau_opt`.

Then: `Delta_{a->b} = C_{a->b} - J*_b`, `R_{a->b} = exp(Delta_{a->b})`.

Sensitivity analysis across `tau_opt in {1e-8, 1e-9, 1e-10}`.

**Note on v1 vs v2:** The original SCIP tier (v1) evaluated a single arbitrary solver optimum under the other representation's weights. This yields an **upper bound** on tie-safe regret, not a lower bound. `R_hat > 1` from an arbitrary optimum does NOT confirm reversal because another optimum within the primary argmin set may be jointly optimal. The v2 two-stage MIP resolves this by minimizing the cross-representation objective over the entire primary-optimal feasible set.

### 3.3 Families and Gate Heterogeneity

| Family | CX-normalized gates | Native gates | Heterogeneity |
|--------|---------------------|--------------|---------------|
| QAOA | {cx} | {rzz} | Uniform->Uniform (different) |
| QFT | {cx} | {cp, swap} | Uniform->Mixed |
| QPE-exact | {cx} | {cp, swap} | Uniform->Mixed |
| BV | {cx} | {cz} | Uniform->Uniform (similar cost) |
| Grover | {cx} | {cx, crz} or {cx, crz, cp} | Uniform->Mixed |
| VQE-RealAmp | {cx} | {cx} | None (control) |
| GHZ | {cx} | {cx} | None (control) |
| DJ | {cx} | {cx} | None (control) |

---

## 4. Results (v2 -- tie-safe corrected)

### 4.1 Summary Statistics

| Metric | Value |
|--------|-------|
| Total records | 96 |
| Valid (computed) | 95 (47 exact, 48 SCIP tie-safe) |
| Strict tie-safe reversals (cx->native) | 8 / 95 |
| Strict tie-safe reversals (native->cx) | 8 / 95 |
| Any tie-safe reversal | 8 / 95 (8.4%) |
| Families with confirmed reversals | 2 (QPE-exact, Grover) |
| Stability theorem violations | 0 / 25 |
| Tau sensitivity: all reversals stable across {1e-8, 1e-9, 1e-10} | Yes |

### 4.2 Per-Family Breakdown

| Family | Instances | Tie-safe reversals | Max R | Notes |
|--------|-----------|-------------------|-------|-------|
| **QPE-exact** | 12 | 3 (25%) | 729 | Bidirectional; exact n=6 + SCIP n=14 |
| **Grover** | 11 | 5 (45%) | overflow (>10^30) | Exact n=6 + SCIP n=12,14,16 (K=3) |
| QAOA | 12 | 0 | 1.0 | Perfectly stable (collinearity) |
| QFT | 12 | 0 | 1.0 | **v1 "reversals" were tie-breaking artifacts** |
| BV | 12 | 0 | 1.0 | Perfectly stable |
| VQE-RealAmp | 12 | 0 | 1.0 | Identical representations (control) |
| GHZ | 12 | 0 | 1.0 | Identical representations (control) |
| DJ | 12 | 0 | 1.0 | Identical representations (control) |

### 4.3 Critical correction: QFT reversals were artifacts

The v1 SCIP tier reported 6 QFT reversals (n=12,14,16; K=2,3) with R up to 27,741.

After tie-safe two-stage correction, **all 6 QFT "reversals" disappear**. The QFT CX-normalized objective landscape has many optimal partitions (recall exact-tier: QFT n=10 K=2 had |argmin_a|=30). The v1 solver happened to return an optimum whose cross-representation cost was high, but within the same argmin set there existed an optimum also optimal under native weights.

This validates the concern that arbitrary single-optimum cross-evaluation can produce false positives.

### 4.4 Confirmed tie-safe reversal instances

| Family | n | K | Tier | R(cx->nat) | R(nat->cx) | Delta(cx->nat) | Delta(nat->cx) | Tau-stable |
|--------|---|---|------|------------|------------|----------------|----------------|------------|
| QPE-exact | 6 | 2 | exact | 1.094 | 81.0 | 0.090 | 4.394 | N/A (exact) |
| Grover | 6 | 3 | exact | 3.43e30 | 4.30e7 | 70.31 | 17.58 | N/A (exact) |
| QPE-exact | 14 | 2 | SCIP-TS | 4.03 | 729.0 | 1.39 | 6.59 | Yes |
| QPE-exact | 14 | 3 | SCIP-TS | 27.48 | 81.0 | 3.31 | 4.39 | Yes |
| Grover | 12 | 2 | SCIP-TS | overflow | 6.27e63 | overflow | overflow | Yes |
| Grover | 12 | 3 | SCIP-TS | overflow | overflow | overflow | overflow | Yes |
| Grover | 14 | 3 | SCIP-TS | overflow | overflow | overflow | overflow | Yes |
| Grover | 16 | 3 | SCIP-TS | overflow | overflow | overflow | overflow | Yes |

**All 8 confirmed reversals are bidirectional** and **all SCIP-tier reversals survive sensitivity analysis across tau_opt in {1e-8, 1e-9, 1e-10}**.

### 4.5 Tau Sensitivity Detail (SCIP reversals only)

| Instance | tau=1e-8 R_ab | tau=1e-9 R_ab | tau=1e-10 R_ab | Verdict |
|----------|---------------|---------------|----------------|---------|
| QPE n=14 K=2 | 4.03 | 4.03 | 4.03 | Stable |
| QPE n=14 K=3 | 27.48 | 27.48 | 27.48 | Stable |
| Grover n=12 K=2 | overflow | overflow | overflow | Stable |
| Grover n=12 K=3 | overflow | overflow | overflow | Stable |
| Grover n=14 K=3 | overflow | overflow | overflow | Stable |
| Grover n=16 K=3 | overflow | overflow | overflow | Stable |

### 4.6 Also corrected: QPE n=12,16 reversals were artifacts

QPE n=12 (K=2,3) and QPE n=16 (K=2,3) reported R up to 833,047 in v1. After tie-safe solve, **all four disappear**. Only QPE n=14 survives -- and with different (lower) R values than v1 reported for some directions (e.g., QPE n=14 K=3: v1 reported R(cx->nat)=2156, v2 tie-safe gives R(cx->nat)=27.48).

---

## 5. Stability Theorem Verification

### 5.1 Theorem Statement (stronger form)

> **Representation-stability condition:** If `m_a > ||w^(b) - w^(a)||_1` (i.e. kappa_{a->b} < 1), then `argmin J_b subset argmin J_a`, hence `R_{a->b} = 1`.

### 5.2 Experimental Verification

In 47 exact-tier instances:

- **25 instances have kappa < 1** (including 24 control instances with kappa=0 and 1 Grover n=4 K=2 with kappa=0.74)
- **All 25 satisfy the predicted stability condition; no empirical inconsistency was observed.**

The theorem is a mathematical proof, not an empirical claim. The experiment verifies internal consistency of the implementation.

### 5.3 Interpretation of kappa >= 1 Cases

In exact-tier instances with kappa >= 1:
- Most still have R = 1 (placement remains stable despite perturbation exceeding margin)
- Only 2/22 exact-tier instances with kappa > 1 actually exhibit reversal
- kappa < 1 is a sufficient condition, not necessary

---

## 6. Key Findings

### 6.1 Finding 1: Representation-Induced Placement Regret Is Real

8/95 instances (8.4%) exhibit strict tie-safe placement reversal, appearing in **2 algorithm families** (QPE-exact, Grover). All are confirmed via either exhaustive enumeration (exact tier) or two-stage lexicographic SCIP (SCIP-TS tier) with sensitivity analysis.

### 6.2 Finding 2: Asymmetry of Regret

All 8 confirmed reversals are **bidirectional** (both R_{a->b} > 1 and R_{b->a} > 1), but with highly asymmetric magnitudes:

- **QPE n=6 K=2:** R(cx->nat) = 1.09 vs R(nat->cx) = 81.0 (factor 74x difference)
- **QPE n=14 K=2:** R(cx->nat) = 4.03 vs R(nat->cx) = 729 (factor 181x difference)

Interpretation: neither representation's optimum is compatible with the other, but the native->CX regret direction is far more severe than CX->native.

### 6.3 Finding 3: Arbitrary Tie-Breaking Can Create False Reversals

**The most important methodological finding of E12 v2.**

6 QFT "reversals" and 4 QPE "reversals" from the v1 single-optimum SCIP tier were **entirely artifacts of arbitrary solver tie-breaking**. The two-stage tie-safe solve eliminated all 10.

This demonstrates that any circuit-cutting study claiming representation-dependent placement effects MUST use tie-safe methodology (full argmin enumeration or lexicographic MIP). Single-optimum cross-evaluation is insufficient.

### 6.4 Finding 4: Family-Dependent Vulnerability

| Category | Families | Mechanism |
|----------|----------|-----------|
| **Reversal-confirmed** | QPE, Grover | Native gates (cp, swap, crz) have QPD costs structurally different from cx, AND the interaction graph topology enables distinct optimal cuts |
| **Stable despite heterogeneity** | QAOA, QFT | QAOA: weight collinearity (Corollary). QFT: many co-optimal partitions absorb perturbation (large argmin sets) |
| **Trivially stable** | BV, VQE, GHZ, DJ | Same gate type or zero perturbation |

### 6.5 Finding 5: QFT Stability Despite Large Absolute Cost Difference

QFT is a surprise result. Despite `J*_CX / J*_native` ratios exceeding 10x at n=16, and despite kappa >> 1, **no tie-safe reversal exists at any tested size**. QFT's large argmin sets (|argmin_a|=30 at n=10 K=2) provide sufficient diversity that some CX-optimal partition is also native-optimal.

This is the strongest evidence that **absolute representation sensitivity does not imply placement sensitivity**.

### 6.6 Finding 6: Regret Magnitude Can Be Extreme

- **Grover n=6 K=3 (exact):** R(cx->nat) = 3.43e30 -- choosing partition based on CX representation incurs >10^30x modeled overhead increase.
- **Grover n>=12 K=3:** R values overflow float64 -- the placement regret is numerically unbounded at these sizes.
- **QPE n=14 K=2:** R(nat->cx) = 729 -- a 3-order-of-magnitude overhead.

These factors are directly resource-interpretable under the specified independent-QPD model.

---

## 7. QAOA Stability: Corollary -- Positive-Scaling Invariance

QAOA ring topology has weight collinearity: `w^(b) = c * w^(a)` with `c = log(rzz_overhead) / log(cx_overhead) approx 0.5`. This guarantees `argmin J_a = argmin J_b` regardless of kappa.

**Corollary.** If `w^(b) = c * w^(a)` for some `c > 0`, then for every feasible partition P: `J_b(P) = c * J_a(P)`, hence `argmin J_a = argmin J_b` and `R_{a->b} = R_{b->a} = 1`.

This explains why absolute overhead sensitivity (QAOA has 2x cost ratio) does not imply placement sensitivity. The perturbation is purely in the "scaling" direction, which preserves partition ordering.

---

## 8. Theoretical Contributions

### 8.1 Proposition: Representation-Regret Bound

For `delta = w^(b) - w^(a)`:

```
0 <= Delta_{a->b} <= ||delta||_1
```

Hence: `R_{a->b} <= exp(||w^(b) - w^(a)||_1)`.

**Proof sketch:** `J_b(P_a) - J_b(P_b) = [J_a(P_a) - J_a(P_b)] + delta^T [z(P_a) - z(P_b)]`. Since P_a optimal for a: first term <= 0. Each component of `z(P_a) - z(P_b)` is in {-1, 0, 1}, so `delta^T [z(P_a) - z(P_b)] <= ||delta||_1`.

### 8.2 Theorem: Representation Stability (stronger form)

```
m_a > ||w^(b) - w^(a)||_1  =>  argmin J_b  subset  argmin J_a  =>  R_{a->b} = 1
```

All 25 theorem-eligible exact-tier instances satisfy the predicted stability condition; no empirical inconsistency was observed.

### 8.3 Corollary: Positive-Scaling Invariance

```
w^(b) = c * w^(a), c > 0  =>  argmin J_a = argmin J_b, R_{a->b} = R_{b->a} = 1
```

### 8.4 Diagnostic: Normalized Stability Ratio

```
kappa_{a->b} = ||w^(b) - w^(a)||_1 / m_a
```

- kappa < 1: guaranteed R = 1 (theorem)
- kappa >= 1: R may be > 1 but is not required to be

---

## 9. Semantic Integrity Verification

All instances (n <= 10) verified unitary equivalence:

| Family | n range | Max deviation | Global phase |
|--------|---------|---------------|--------------|
| QAOA | 4--10 | 1.33e-15 | ~1.0 |
| QFT | 4--10 | 1.56e-15 | ~1.0 |
| QPE | 4--10 | 3.11e-15 | ~1.0 |
| BV | 4--10 | 0 | ~1.0 |
| Grover | 4--8 | 3.23e-14 | ~1.0 |
| VQE | 4--10 | 1.66e-15 | 1.0 |
| GHZ | 4--10 | 4.27e-17 | ~1.0 |
| DJ | 4--10 | 4.27e-17 | ~1.0 |

All pass. Both representations implement the same unitary (up to global phase).

---

## 10. Environment

- **Qiskit:** 2.5.1
- **Qiskit Addon Cutting:** 0.10.0
- **PySCIPOpt:** 6.2.1
- **MQT Bench:** 2.2.2
- **Transpile settings:** `optimization_level=1, seed_transpiler=0, coupling_map=None`
- **Parameter binding:** all source parameters = pi/4
- **SCIP time limit:** 600s per solve (per stage)
- **Symmetry breaking:** q0 fixed to fragment 0
- **Tolerance:** 1e-10 for regret classification
- **Tau_opt (SCIP tie-safe):** 1e-9 primary, sensitivity at {1e-8, 1e-10}

---

## 11. Limitations and Caveats

1. **Draper QFT Adder** failed ingestion for native representation (source fingerprint mismatch or unsupported gates). Excluded.

2. **Grover n >= 10 exact tier**: overflow due to very large circuits (thousands of 2-qubit gates). Grover n=10 K=2 excluded from exact tier.

3. **SCIP tie-safe tier** provides solver-tolerance tie-safe regret, not mathematically exact. The two-stage MIP constrains `J_a(P) <= J*_a + tau_opt + scip_feastol`. Sensitivity analysis across three tau values confirms stability.

4. **Collinearity effect** (QAOA): kappa bound is conservative for circuits with proportional weights. The positive-scaling corollary provides the tight characterization.

5. **Grover overflow**: at n >= 12, log-costs are so large that exp() overflows float64. The reversal is real but the magnitude R cannot be represented numerically. Report as R = overflow.

---

## 12. Implications for Paper

### 12.1 Current Paper Statement

> "Use correct heterogeneous QPD weights."

### 12.2 Upgraded Statement (with E12)

> "Circuit representation can alter the independent-QPD-optimal partition itself; this effect occurs across multiple algorithm-derived families and can induce large modeled placement regret."

### 12.3 Proposed Paper Structure

**Section V-L: Representation-Induced Placement Regret** (~0.75--1.25 pages)

1. Keep Table X (absolute representation sensitivity)
2. Definition: `Delta_{a->b}`, `R_{a->b}`
3. **Proposition** (Representation-regret bound): `R_{a->b} <= exp(||delta||_1)`
4. **Theorem** (Representation stability, stronger form): `m_a > ||delta||_1 => argmin J_b subset argmin J_a`
5. **Corollary** (Positive-scaling invariance): `w^(b) = c w^(a) => R = 1`
6. Table: Per-family tie-safe placement regret results
7. Discussion: QFT stability vs QPE/Grover instability

### 12.4 Evidence Strength Assessment

Results correspond to a mixture of **Case A** and **Case B** in the evaluation framework:

- **8/95 strict tie-safe reversals** across **2 algorithm families** (QPE, Grover)
- Exact witnesses with optimum-set overlap = 0
- SCIP-tier reversals survive sensitivity analysis across 3 tolerance levels
- Max R: overflow (>10^30 for Grover), 729 for QPE
- Stability theorem verified (25/25)
- QFT "false positives" from v1 eliminated by tie-safe methodology
- Positive-scaling corollary explains QAOA stability

The result is sufficient to constitute a **supporting contribution** and potentially a second conceptual result, especially because the tie-safe methodology itself is a contribution (demonstrates that single-optimum methods give unreliable placement-regret estimates).

---

## 13. Raw Data Tables

### Table 1: Exact Tier -- Heterogeneous Families (selected)

| Family | n | K | J*_CX | J*_nat | R(cx->nat) | R(nat->cx) | kappa | m_a | overlap |
|--------|---|---|-------|--------|------------|------------|-------|-----|---------|
| QAOA | 4 | 2 | 8.79 | 4.39 | 1.00 | 1.00 | 1.00 | 8.79 | 2/2x2 |
| QAOA | 8 | 2 | 52.73 | 26.37 | 1.00 | 1.00 | 7.00 | 8.79 | 5/5x5 |
| QAOA | 10 | 2 | 87.89 | 43.94 | 1.00 | 1.00 | 13.00 | 8.79 | 2/2x2 |
| QFT | 6 | 2 | 46.14 | 13.16 | 1.00 | 1.00 | 4.38 | 13.18 | 2/6x2 |
| QFT | 8 | 2 | 70.31 | 12.51 | 1.00 | 1.00 | 8.28 | 13.18 | 1/3x1 |
| QFT | 10 | 2 | 116.45 | 18.32 | 1.00 | 1.00 | 13.50 | 13.18 | 2/30x2 |
| **QPE** | **6** | **2** | **35.16** | **12.21** | **1.09** | **81.0** | **10.81** | **4.39** | **0/1x1** |
| QPE | 8 | 2 | 70.31 | 18.69 | 1.00 | 1.00 | 14.89 | 6.59 | 1/3x1 |
| QPE | 10 | 2 | 101.07 | 21.38 | 1.00 | 1.00 | 36.01 | 4.39 | 1/1x1 |
| Grover | 4 | 2 | 70.31 | 70.31 | 1.00 | 1.00 | **0.74** | 8.79 | 1/1x1 |
| **Grover** | **6** | **3** | **650.38** | **563.36** | **3.4e30** | **4.3e7** | **18.33** | **17.58** | **0/1x1** |
| Grover | 8 | 2 | 2109.34 | 2671.83 | 1.00 | 1.00 | 14.77 | 140.62 | 1/1x1 |

### Table 2: SCIP Tie-Safe Tier -- Confirmed Reversals

| Family | n | K | J*_CX | J*_nat | R(cx->nat) | R(nat->cx) | disagree | tau-stable |
|--------|---|---|-------|--------|------------|------------|----------|------------|
| QPE | 14 | 2 | 202.14 | 28.19 | 4.03 | 729.0 | 2 | Yes |
| QPE | 14 | 3 | 272.46 | 38.29 | 27.48 | 81.0 | 6 | Yes |
| Grover | 12 | 2 | 24301 | 35683 | overflow | 6.27e63 | 6 | Yes |
| Grover | 12 | 3 | 34760 | 53525 | overflow | overflow | 3 | Yes |
| Grover | 14 | 3 | 89234 | 138531 | overflow | overflow | 10 | Yes |
| Grover | 16 | 3 | 240245 | 394375 | overflow | overflow | 12 | Yes |

### Table 3: SCIP Tie-Safe Tier -- Former "Reversals" Now Resolved as R=1

| Family | n | K | v1 R(cx->nat) | v2 tie-safe R(cx->nat) | v2 tie-safe R(nat->cx) |
|--------|---|---|---------------|------------------------|------------------------|
| QFT | 12 | 2 | 27,741 | 1.0 | 1.0 |
| QFT | 12 | 3 | 227 | 1.0 | 1.0 |
| QFT | 14 | 2 | 5,882 | 1.0 | 1.0 |
| QFT | 14 | 3 | 7,382 | 1.0 | 1.0 |
| QFT | 16 | 2 | 24,522 | 1.0 | 1.0 |
| QFT | 16 | 3 | 14,425 | 1.0 | 1.0 |
| QPE | 12 | 2 | 4,560 | 1.0 | 1.0 |
| QPE | 12 | 3 | 423 | 1.0 | 1.0 |
| QPE | 16 | 2 | 833,047 | 1.0 | 1.0 |
| QPE | 16 | 3 | 280,610 | 1.0 | 1.0 |

---

## 14. Conclusion

E12 demonstrates that circuit representation can alter the independent-QPD-optimal partition itself. After tie-safe correction:

1. **8/95 confirmed tie-safe reversals** across **2 algorithm families** (QPE-exact, Grover), all bidirectional, all tau-stable
2. **10 false positives from v1 eliminated** by two-stage lexicographic SCIP, demonstrating that tie-safe methodology is essential
3. **QFT: unexpectedly robust** despite 10x absolute cost difference -- large argmin sets absorb representation perturbation
4. **QAOA: structurally stable** via positive-scaling invariance (weight collinearity corollary)
5. **Stability theorem verified** on all 25 eligible exact-tier instances
6. **Regret magnitudes can be extreme**: overflow for Grover, 729x for QPE

The combination of confirmed reversals, clean theoretical framework (proposition + theorem + corollary), and the methodological lesson about tie-safe computation constitutes a contribution that strengthens the CertiCut paper by adding:

> **"The optimization target itself is compiler-representation dependent. We characterize both the resulting placement regret and sufficient conditions for placement stability."**
