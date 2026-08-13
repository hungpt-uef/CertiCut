# CertiCut Phase 9.1 Frozen Outline

## Submission Envelope

- Working title: **CertiCut: Certified Anytime Optimization for Sampling-Aware Quantum Circuit Cutting via Polyhedral Relaxations**.
- Budget: 8 main pages excluding references and appendix. Scale section allocations proportionally if the venue differs; do not expand scope.
- Evidence freeze: `results/final_manifest.json`, dated 2026-08-11. All numerical claims must trace to `paper/claims.md` or its frozen raw artifact hash.
- Scope throughout: exact balanced two-fragment (`K=2`) partitioning; independent Qiskit Addon Cutting 0.10 QPD costs; logical all-to-all circuit representation.

## Page Budget

| Part | Target pages | Primary purpose |
| --- | ---: | --- |
| Introduction | 1.00 | Problem, gap, contributions |
| Background and formulation | 0.85 | QPD objective and `K=2` problem |
| CertiCut | 2.20 | Relaxation, separation, heuristic, certificate |
| Experimental methodology | 0.70 | Corpus, protocol, baselines, metrics |
| Results | 1.95 | Six research questions |
| Related work | 0.55 | Position against cutting and certified optimization |
| Limitations and conclusion | 0.45 | Scope, closing claim |
| Figures/tables/caption overhead | 0.30 | Included in section allocations |

## Figure and Table Placement

| Asset | Placement | Job | Source |
| --- | --- | --- | --- |
| Fig. 1, CertiCut architecture | Sec. 1, after contribution paragraph | Show circuit-to-graph objective, H2 upper bound, B2S lower bound, certified B&B, and `LB <= OPT <= UB` | `figures/fig_certicut_architecture.tex` |
| Fig. 2, anytime certificate cactus | Sec. 4, RQ2 | Show proof/certificate progress across all 420 E1 instances | `figures/fig_anytime_certificate.pdf` |
| Fig. 3, scaling/runtime composition | Sec. 4, RQ3 | Show aggregate scaling and optimizer dominance | `figures/fig_scaling_composition.pdf` |
| Fig. 4, native-QPD QAOA representation | Sec. 4, RQ4 | Show paired CX-normalized versus native representation result | `figures/fig_native_qaoa_representation.pdf` |
| Table 1, controlled ablation | Sec. 4, RQ1 | Establish B2S as proof-performance driver | `tables/table_ablation.md` |
| Table 2, anytime full-denominator results | Sec. 4, RQ2 | Report availability, proof rate, and factor thresholds | `tables/table_anytime.md` |
| Table 3, scaling | Sec. 4, RQ3 | Report size-stratified proof, time, memory | `tables/table_scaling.md` |
| Table 4, native-QPD results | Sec. 4, RQ4 | Quantify representation sensitivity | `tables/table_native_qpd.md` |
| Table 5, operational validation | Sec. 4, RQ6 | Match predicted and executed reconstruction overhead | `tables/table_operational.md` |

Move the n=40 family-tail table to appendix unless the main-page budget has room. Keep its result in RQ3 prose: observed family stratification, not a causal density claim.

## 1. Introduction (1.00 page)

1. Limited hardware motivates circuit cutting.
2. Gate cuts alter QPD sampling overhead; a returned partition without an optimality gap cannot quantify decision quality when interrupted.
3. CertiCut optimizes a gate-dependent log-QPD objective for exact balanced `K=2` partitions, then maintains an incumbent upper bound and global lower bound.
4. Fig. 1 architecture.
5. Contributions, exactly four:
   - Certified anytime optimization: safe-stop `LB <= OPT <= UB`, factor `F = exp(UB - LB)`.
   - Polyhedral strengthening: B2S root separation materially improves controlled proof completion.
   - Gate-dependent objective: minimizing cut count differs from minimizing independent-QPD overhead.
   - Native representation sensitivity: legal QPD representations can alter the predicted optimum under the stated Qiskit 0.10 model.
6. State `K=2` specialization before contributions end. Do not frame a general multi-fragment solver.

## 2. Background and Problem Formulation (0.85 page)

### 2.1 Independent QPD Circuit Cutting

- Define per-gate QPD overhead `rho_g = (sum_i |a_i|)^2`.
- For a partition `P`, define crossed-gate overhead `Gamma(P) = product_{g in S(P)} rho_g`.
- Qualify: this is independent QPD under Qiskit Addon Cutting 0.10, not joint-QPD or physical-shot optimality.

### 2.2 Log-Domain Interaction Graph

- Define `J(P) = log Gamma(P) = sum_{g in S(P)} log rho_g`.
- Aggregate `w_ij = sum_{g in G_ij} log rho_g`.
- Define crossing indicator `x_ij`; then `J(P) = sum_(i,j in E) w_ij x_ij`.
- **Proposition 1 (objective equivalence).** Under independent gate QPD, the weighted interaction-graph objective equals the gate-level log-overhead objective. Proof: regroup crossed gates by endpoint pair.

### 2.3 V1 Feasible Space

- Define binary assignment `z_i` and exact balanced two-fragment capacity.
- State all benchmarked sizes are even; each fragment contains `n/2` qubits.
- Define the equivalent integral cut cardinality `sum_{i<j} x_ij = floor(n^2/4)`.
- Do not defer this restriction to Limitations.

## 3. CertiCut (2.20 pages)

### 3.1 Exact MILP Oracle (0.20 page)

- Present the compact exact formulation as validation oracle and exact solver reference.
- Keep implementation details out of the main paper.

### 3.2 Basic LP Relaxation (0.25 page)

- Relax binary variables to `[0,1]`.
- Give XOR envelope linking `z_i`, `z_j`, and `x_ij`.
- Explain fractional cut geometry makes the basic bound weak.

### 3.3 B2S Polyhedral Strengthening (0.65 page)

- Add balanced cut cardinality and triangle/metric inequalities.
- Show one representative triangle inequality family, state symmetric variants compactly.
- **Proposition 2 (relaxation validity).** Every integral exact-balanced partition satisfies the XOR envelope, cardinality equality, and triangle system. Therefore the strengthened LP optimum is a valid lower bound. Proof: evaluate constraints for binary partition labels; minimization over a superset yields a lower bound.

### 3.4 Root Separation (0.25 page)

- B2S loop: solve LP, identify violated triangles, add them, repeat to no selected violation.
- Freeze the resulting root cut pool for tree search.
- Mention node-level separation only in ablation discussion: not retained because its runtime cost outweighed its small node-count benefit.

### 3.5 H2 Primal Heuristic (0.20 page)

- Seed a balanced feasible partition, apply weighted pair swaps.
- Define `g(a,b) = D(a) + D(b) - 2w_ab`.
- Position H2 as upper-bound construction, not proof driver.

### 3.6 Certified Best-Bound Branch-and-Bound (0.65 page)

- Best-bound node selection; most-fractional branching.
- At every completed safe LP or B&B boundary, define `LB = min(UB, min_{N in frontier} LB_N)`.
- Define `Delta = UB - LB`, `F = exp(Delta)`.
- **Proposition 3 (anytime certificate).** At every safe stopping point, `LB <= OPT <= UB`; hence `Gamma_incumbent / Gamma* <= exp(UB - LB)`. Proof: incumbent feasibility gives upper bound; every unexplored feasible completion belongs to a frontier node whose LP bound is no larger than its integral objective; exhausted frontier yields closure.
- State requested deadlines are soft. A snapshot is reported only after a completed safe boundary; no later certificate is backfilled.

## 4. Experimental Methodology (0.70 page)

### 4.1 Frozen Protocol

- Cite manifest version stack, tolerance `1e-9`, fixed seeds, raw SHA-256 hashes.
- E1: 420 synthetic CNOT-only `K=2` instances, seven topology families, `n in {16,20,24,26,32,40}`, ten seeds each, isolated processes, requested 60 s safe deadline.
- E2/E3: real MQT Bench CX-normalized/native-QPD circuits.
- E4: 60 Qiskit practical-Qmax records, separate backjump-budget semantics; never compare as equal-wall-clock results.

### 4.2 Metrics and Baselines

- Primary: proof status, certificate availability, factor threshold, optimizer/end-to-end runtime, peak memory, exact reconstruction error.
- Bootstrap: 2,000 resamples, seed `20260811`, E1 full denominator 420.
- KaHIP: feasible-solution baseline, not a certificate baseline.
- Qiskit automatic cut finder: practical-Qmax contextual baseline with preserved `minimum_reached` status.

## 5. Results (1.95 pages)

### RQ1. How much does polyhedral strengthening improve proof performance?

- Table 1.
- Report `41/90` to `90/90` proof completion within 100 nodes from basic to B2S-root regimes.
- H2 leaves basic proof count unchanged; B2S is the principal algorithmic contribution.

### RQ2. How quickly does CertiCut return quantitative certificates?

- Fig. 2 and Table 2.
- Report `343/420 (81.7%)` proven at 2 s; `417/420 (99.3%)` proven by 60 s.
- At 60 s, certificates available for `420/420`; three non-proven runs retain valid final factors.
- Use full denominator for every requested time. Avoid a long progressive-near-optimality narrative: most successful runs reach proof directly; unfinished work retains a quantitative bound.

### RQ3. How does performance vary by topology and size?

- Fig. 3 and Table 3.
- Report `67/70` proofs at `n=40`, median optimizer time `7.805 s`, p90 `42.665 s`.
- Appendix family table: community `0.809 s`, nearest-neighbor `1.646 s`, QAOA ring `5.367 s`; random `18.344 s`, dense `24.070 s`, weighted-random `37.215 s` median end-to-end at `n=40`.
- Phrase as observed family stratification. Do not claim density statistically causes runtime.

### RQ4. Does native/gate-dependent QPD modeling matter?

- Explain counterexample: two iSWAP cuts cost `49^2 = 2401`; three CX cuts cost `9^3 = 729`.
- Table 4 and Fig. 4.
- Paired QAOA `n=16`, fixed `pi/4`: `J*_CX = 158.200`, `J*_native = 79.100`, ratio `2.25e34`.
- Qualify every such statement: under respective Qiskit 0.10 independent-QPD representations; not an intrinsic physical-shot claim.

### RQ5. How does specialization relate to practical automatic cutting?

- KaHIP framing: report it as an excellent fast feasible baseline; CertiCut supplies optimality knowledge or a worst-case factor.
- Qiskit framing: practical-Qmax allows more fragments; compare objectives only on exact balanced two-fragment overlap.
- Report `24/24` Qiskit-proven practical records with no observed K=2 penalty, then immediately state this is limited evidence, not general equivalence.

### RQ6. Are solutions operationally executable?

- Table 5.
- Report QAOA native RZZ and VQE CX exact reconstruction errors near machine precision.
- State only overhead reconstruction validation; no finite-shot variance study.

## 6. Related Work (0.55 page)

- Circuit cutting and QPD sampling-overhead minimization.
- Automatic partitioning/cut finding, including Qiskit Addon Cutting.
- Exact balanced graph partitioning, cut polytope/metric inequalities, and branch-and-bound certificates.
- Novelty audit requirement before draft freeze: explicitly test whether a prior circuit-cutting method already provides an interrupted global multiplicative sampling-overhead certificate with comparable QPD scope. If found, narrow novelty language to the distinct formulation, strengthening, or protocol difference.

## 7. Limitations and Conclusion (0.45 page)

- Exact balanced `K=2`; no general multi-fragment equivalence claim.
- Independent QPD only; no joint-QPD optimum.
- Qiskit Addon Cutting 0.10 representation/decomposition dependence.
- Observed `n=40` hard tail; no large-scale scalability claim.
- Logical all-to-all model; no hardware topology, noise, or routing.
- Exact reconstruction; no finite-shot variance analysis.
- Conclusion: CertiCut turns interruption from an unqualified incumbent into a quantitative, auditable certificate inside its explicit scope.

## Claim Language Lock

| Claim | Allowed wording | Prohibited wording |
| --- | --- | --- |
| Certification | Valid at completed safe boundaries; final 60 s time-limit returns valid certificate | Hard real-time guarantee; certificate available before first safe boundary |
| B2S | Dominates controlled proof completion in the stated ablation | Universally best relaxation or branching policy |
| Native QPD | Materially changes predicted independent-QPD overhead under Qiskit 0.10 | Intrinsic physical shot reduction |
| n=40 | Family-stratified observed tail | Density causes difficulty |
| K=2 | No observed penalty on 24 stated practical cases | K=2 is generally equivalent to practical cutting |
| Qiskit/KaHIP | Complementary feasible/practical baselines | Equal-wall-clock certified comparisons |

## Draft Order

1. Sections 2 and 3, including Proposition 1--3 and Fig. 1.
2. Section 4 methodology and Section 5 results from frozen tables/figures.
3. Section 7 limitations.
4. Section 6 related work and novelty audit.
5. Section 1 introduction.
6. Abstract and conclusion last.
