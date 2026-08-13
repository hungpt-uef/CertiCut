# CertiCut-K/J/H Experimental Report

Ngày: 12/08/2026

## Trạng thái

**PASS, WITH EXPLICIT SCOPE BOUNDARIES.** CertiCut-K now solves capacitated independent-QPD K-way graph partitioning through SCIP with solver-tolerance primal/dual bounds. Existing theorem-backed K=2 parallel joint-QPD, exact branch reconstruction, and offline hardware-aware hypergraph placement were rerun. Controlled Aer noise scenarios and fragment-local transpilation diagnostics were added.

This is not one monolithic exact K-way joint-QPD hardware-mapping solver. The valid result is a layered evidence chain:

```text
CertiCut-K: exact-capacity independent-QPD SCIP MIP with solver-tolerance LB/UB.
CertiCut-J: existing legal K=2 parallel joint-QPD oracle and exact reconstruction.
CertiCut-H: existing offline FakeBrisbane placement MILP plus new topology diagnostics.
CertiCut-N: controlled Aer sensitivity, not a calibrated-QPU prediction.
```

## Delivered Code

| Component | File | Scope |
| --- | --- | --- |
| K-way optimizer | `certicut/optimization/k_partition.py` | independent QPD, arbitrary K, per-fragment lower/upper capacities, SCIP LB/UB |
| K-way experiments | `scripts/run_certicut_k_experiments.py` | 12 deterministic K=2/K=3 cases, topology diagnostics, Aer scenarios |
| Fragment topology evaluator | `certicut/hardware/evaluation.py` | local retained-gate transpilation on all-to-all, line, grid |
| Aer controlled scenarios | `certicut/hardware/evaluation.py` | synthetic depolarizing and readout model |
| Log intervals | `certicut/optimization/intervals.py` | directed-decimal enclosure of reported float QPD inputs |
| Joint-QPD executor | `certicut/costs/joint_parallel.py`, `certicut/qiskit_bridge/joint_parallel.py` | existing legal K=2 parallel blocks |
| Hardware placement MILP | `certicut/optimization/hypergraph_milp.py` | existing joint-block surrogate plus exact logical/physical placement |

## CertiCut-K Formulation

For qubit `i`, fragment `k`, interaction edge `e=(i,j)`:

```text
x[i,k] = 1: qubit i belongs to fragment k
y[e,k] = 1: endpoints of e both belong to k
z[e]   = 1: endpoints of e are split
```

```text
sum_k x[i,k] = 1
L[k] <= sum_i x[i,k] <= U[k]
y[e,k] <= x[i,k]
y[e,k] <= x[j,k]
y[e,k] >= x[i,k] + x[j,k] - 1
z[e] + sum_k y[e,k] = 1
minimize sum_e log(rho_e) z[e]
```

`K=2` B2S constraints were deliberately not copied into K-way. The new formulation uses the valid assignment/locality linearization rather than bisection-only cut facets.

SCIP returns primal and dual bounds. CertiCut reports:

```text
LB <= OPT <= UB
F = exp(UB - LB)
```

All closed records below have `F=1`. Certificate kind remains `solver_tolerance`; it is not a formal rational-arithmetic proof.

### Bound Semantics

For any feasible K-way partition `P`, fixed independent-QPD costs `w[e]=log(rho[e]) >= 0`, and solver-reported tolerance-valid bounds:

```text
J(P) = sum_e w[e] 1[f(u_e) != f(v_e)]
LB <= J* <= UB
Gamma(P) = exp(J(P))
```

the incumbent satisfies `Gamma_inc / Gamma* <= exp(UB - LB)`. This algebra holds for every `K >= 2` and all feasible lower/upper capacities. It remains conditional on validity of backend floating-point bounds. Current terminology is **solver-tolerance anytime model-overhead bounds**, not formally verified numerical certification.

For exact capacities `|F_k|=n_k`, complete-pair cross cardinality generalizes balanced bisection:

```text
sum_{i<j} 1[f(i) != f(j)] = C(n, 2) - sum_k C(n_k, 2).
```

For `(3,3)`, this is `9`; for `(4,3,3)`, `33`. No equality is imposed for lower/upper-only capacities.

## K-Way Results

Setup:

```text
families: nearest_neighbor, community, random
n:        8, 10
K:        2, 3
capacities:
  n=8:  K=2 (4,4); K=3 (3,3,2)
  n=10: K=2 (5,5); K=3 (4,3,3)
cost: legacy CX independent QPD, rho=9 per cut gate
SCIP time limit: 30 s per instance
```

| Family | n | K | Capacity | Gamma | SCIP nodes | Runtime |
| --- | ---: | ---: | --- | ---: | ---: | ---: |
| nearest-neighbor | 8 | 2 | (4,4) | 9 | 1 | 0.012 s |
| nearest-neighbor | 8 | 3 | (3,3,2) | 729 | 1 | 0.018 s |
| nearest-neighbor | 10 | 2 | (5,5) | 81 | 1 | 0.012 s |
| nearest-neighbor | 10 | 3 | (4,3,3) | 729 | 1 | 0.055 s |
| community | 8 | 2 | (4,4) | 81 | 1 | 0.013 s |
| community | 8 | 3 | (3,3,2) | 59,049 | 1 | 0.017 s |
| community | 10 | 2 | (5,5) | 81 | 1 | 0.021 s |
| community | 10 | 3 | (4,3,3) | 4,782,969 | 5 | 0.170 s |
| random | 8 | 2 | (4,4) | 531,441 | 3 | 0.056 s |
| random | 8 | 3 | (3,3,2) | 43,046,721 | 1 | 0.018 s |
| random | 10 | 2 | (5,5) | 6,561 | 3 | 0.096 s |
| random | 10 | 3 | (4,3,3) | 43,046,721 | 7 | 0.188 s |

Result: `12/12` SCIP optima. K=3 incurs substantially higher independent-QPD sampling overhead in this capacity-limited corpus. This is expected from more mandatory boundaries; it does not imply that K=3 is intrinsically worse once heterogeneous hardware, joint QPD, or parallel throughput is modeled.

## E9 Replicated Heterogeneous Scalability

The K-way headline was extended with the validated heterogeneous QPD palette:

```text
CX, CZ, iSWAP, RZZ(pi/8), RZZ(pi/4), RZZ(pi/2)
families: random_matching, community_matching, weighted_repeat
n: 20, 32, 40, 60
K: 2, 3, 4, 5
capacities: exact near-balanced
seeds: 3 per family--size--K cell
SCIP budget: 10 s / instance; threads: 1; records: 144
```

| Family | Closed / 48 | All-seed-closed largest K,n | Timeout boundary |
| --- | ---: | --- | --- |
| random matching | 20 | K=2,n=40; K=5,n=20 | K>=3,n>=32; n=60,K=2 seed sensitive |
| community matching | 37 | K=3,n=60; K=4,n=40 | K=5,n>=32; K>=4,n=60 |
| weighted repeat | 44 | K=3,n=60; K=4,n=40 | K>=4,n=60; K=5,n>=32 |
| total | 101 / 144 | n=60,K=3 | family/seed dependent |

K=2 closes `34/36`; the two open records are random matching at `n=60`. K>=3 is feasible and closes at `n=60` for structured families, but the assignment/locality MILP becomes difficult for random matching. Median random-matching open factors: `n=32,K=5: 10^15.47`, `n=60,K=4: 10^44.84`. This negative evidence is retained: the baseline is correct and transparent, not a claim of universal large-K scalability.

### Formulation-Strengthening Ablation

The sparse assignment/locality LP has a zero-objective fractional solution under exact capacities. We tested the natural remedy implied by the K-way cross-pair identity: add all nonedge pair variables, exact complete-pair cardinality, complete-metric triangles, and equal-capacity label anchoring. On 36 E9 records (`n={20,32}`, `K={3,4}`, three families, three seeds), 5 s per configuration:

| Configuration | Closed | Median runtime |
| --- | ---: | ---: |
| Sparse base | 31 / 36 | 1.48 s |
| Symmetry anchor only | 29 / 36 | 1.56 s |
| All-pair cardinality + symmetry | 6 / 36 | 4.66 s |
| All-pair cardinality + metric + symmetry | 6 / 36 | 4.98 s |

The dense extensions are valid but harm end-to-end SCIP behavior at this scale. Production CertiCut-K therefore uses the sparse MIP with an equal-capacity `qubit 0 -> fragment 0` anchor. This is a negative strengthening result, not a claim that the sparse LP is strong.

### K-Way Baseline Boundary

KaHIP K-way was evaluated as an available graph-partitioning heuristic using scaled integer log-QPD edge weights and post-hoc CertiCut objective evaluation. It produces many capacity-incompatible partitions at non-divisible near-balanced cells, so it is not a fair exact-capacity baseline for the full E9 matrix. Qiskit's automatic cut finder has a width-constrained gate/wire-cut model, not the same fixed-K graph-partitioning formulation. Nakamura et al. (2025) and Fröhler et al. (2026) are now cited and distinguished in the paper; their released implementations were not available in this environment for a claimable head-to-head result.

### Direct Weighted K-Way Baseline

A new independent multistart greedy-swap baseline uses the exact E9 capacity vector and aggregate log-QPD edge weights. Unlike KaHIP, it returns feasible partitions for `144/144` records. CertiCut's SCIP lower bound evaluates each baseline partition without claiming the baseline's own certificate:

```text
Gamma(P_heuristic) / Gamma* <= exp(J(P_heuristic) - LB_SCIP)
```

| Metric | Value |
| --- | ---: |
| Baseline median runtime | 21.6 ms |
| SCIP-closed comparison records | 101 |
| Baseline-optimal records | 23 / 101 |
| Median regret upper factor | 28.05 |
| p90 regret upper factor | 3.32e10 |
| Maximum regret upper factor | 5.80e20 |

This is a direct weighted exact-capacity K-way comparison, not a reproduction claim for Nakamura or Fröhler.

For the `43` E9 records that hit SCIP's deadline, the same valid but loose heuristic-regret bound has median `5.79e15`, p90 `5.81e30`, and maximum `9.97e31`. This demonstrates why the paper reports global factors rather than treating time-limited incumbent comparisons as optima.

### E10 Algorithm-Derived K-Way

Native-QPD MQT Bench matrix:

```text
families: QAOA, QFT, exact QPE, Draper-QFT-adder
n: 20, 24, 32
K: 2, 3, 4
budget: 10 s SCIP
valid records: 36
additional recorded failures: 3 VQE circuits with unsupported native QPD gates
```

| K | Closed / 12 |
| --- | ---: |
| 2 | 11 |
| 3 | 3 |
| 4 | 1 |

Total: `15/36` valid algorithm-derived records close. This preserves the E9 conclusion on non-synthetic workloads: structured K-way instances can close, while larger K rapidly weakens solver-tolerance guarantees.

## Final Pre-Submit Corrections

- Renumbered propositions uniquely from 1 through 6.
- Changed `nine experiment sets` to `ten experiment sets; E8 is supplementary`.
- Corrected abstract wording: baseline `returns feasible partitions`, never `solves` instances.
- Defined core scope as static logical-qubit partitioning with gate cuts, not temporal gate-placement optimization.
- Corrected Fröhler et al. author metadata: Fiona Jiali Fröhler and Yannick Stade.
- Expanded artifact-availability text with E9/E10 generators, raw records, capacity vectors, gate-cost order, baseline policy, and explicit VQE failures.
- Reworded deterministic QPD cost cycling: seed-independent, but residual ordering effects remain a stated limitation.

## Lexicographic 5% Hardware Budget

New API:

```text
stage 1: minimize J(P) = log(Gamma(P))
stage 2: minimize R(P)
         subject to J(P) <= J* + log(1.05)
```

`R(P)` is a declared local-edge routing surrogate, not exact hardware mapping. The first 12-instance probe completed `10/12` second stages. Every completed instance returned the sampling optimum, `Gamma/Gamma*=1`; no routing-improvement witness appeared. This is a valid negative result: discrete independent-QPD overheads make a 5% budget too narrow here. Retain the API, not a hardware-quality claim. Next matrix: real placement-derived costs, factor sweep `{1.05,1.25,2.0}`, cases with multiple near-optimal partitions.

## Log Intervals

Each cut plan additionally records an 80-decimal directed interval for the reported sum of `log(rho)` values. Example, two CX cuts:

```text
[4.3944491546724387655809809476901028185899622312909978069387773345499771728744356,
 4.3944491546724387655809809476901028185899622312909978069387773345499771728744360]
```

This removes display ambiguity in log aggregation. It does not make SCIP floating-point branch-and-bound a formal exact-MILP certificate, and it does not validate an overhead supplied only as a binary float. Exact SCIP mode needs rationalized input plus an independently justified enclosure of each irrational logarithm.

## Joint-QPD Operational Rerun

The existing restricted theorem class was rerun:

```text
K=2 fixed bipartition
one common parallel layer
pairwise-disjoint crossing numeric two-qubit unitaries
exact branch enumeration
product input over the cut
```

| Legal block | Independent Gamma | Joint Gamma | Max reconstruction error |
| --- | ---: | ---: | ---: |
| single CX | 9 | 9 | 6.67e-16 |
| single RZZ(pi/4) | 5.828427 | 5.828427 | 1.11e-16 |
| single iSWAP | 49 | 49 | 5.60e-17 |
| two parallel CX | 81 | 49 | 1.39e-16 |
| parallel CX + RZZ(pi/4) | 52.456 | 33.970563 | 3.10e-17 |
| two parallel iSWAP | 2,401 | 961 | 1.12e-16 |
| two parallel RZZ(0.1) | 4.058 | 2.014319 | 0 |

All 8 legal micro-corpus cases reconstruct six Pauli-product observables to below `1e-10`. The parallel-CX witness proves a strict theorem-backed reduction `81 -> 49` under this policy.

Existing `PJ` pattern MILP and certified PJ B&B remain K=2 only. Generic HiGHS remains the stronger production choice for that current joint objective; no superiority claim is made for custom PJ B&B.

## Hardware-Aware Offline Rerun

The existing exact-placement hypergraph MILP was rerun on the frozen official `FakeBrisbane` snapshot:

```text
backend: fake_brisbane
source: qiskit_ibm_runtime_fake_provider
physical sites: 127
coupling edges: 144
snapshot SHA-256: e694bcbfd96fd71c25f0433b0f4cf79c2312203764fc2ec79197e20b01019a2c
families: QAOA-style, VQE Real-Amplitudes
n: 6, 8, 10, 12, 14
K: 2, 3
objective: joint-block Schmidt surrogate + routing + readout + gate-error terms
```

`20/20` configurations returned HiGHS optima. Every instance included a true arity-three-or-higher temporal-spatial block.

Observed solve-time boundary:

| Family | n | K | Runtime |
| --- | ---: | ---: | ---: |
| QAOA-style | 6 | 2 | 0.055 s |
| QAOA-style | 10 | 3 | 9.875 s |
| QAOA-style | 12 | 2 | 31.631 s |
| QAOA-style | 14 | 2 | 167.825 s |
| QAOA-style | 14 | 3 | 311.817 s |
| VQE Real-Amplitudes | 14 | 2 | 1.588 s |
| VQE Real-Amplitudes | 14 | 3 | 1.059 s |

The exact placement formulation is tractable for the tested VQE instances but has a clear QAOA-tail cost. This is an offline calibration-aware surrogate benchmark, not live-QPU performance evidence.

## New Fragment Transpilation Diagnostics

After CertiCut-K partitioning, retained local gates were transpiled with `GenericBackendV2`, fixed seed, and topology-specific coupling maps. Cut gates are deliberately omitted because they belong to QPD reconstruction, not one local fragment circuit.

| CertiCut-K witness | Topology | Mapped 2Q gates | Added routing 2Q gates | Max fragment depth |
| --- | --- | ---: | ---: | ---: |
| community, n=10, K=2 | all-to-all | 14 | 0 | 6 |
| community, n=10, K=2 | line | 32 | 12 | 13 |
| community, n=10, K=2 | grid | 23 | 4 | 10 |
| random, n=10, K=2 | all-to-all | 14 | 0 | 7 |
| random, n=10, K=2 | line | 24 | 8 | 11 |
| random, n=10, K=2 | grid | 17 | 3 | 9 |

Routing columns are transpiler expansion counts, not literal `swap` instruction counts. The transpiler can decompose routing without preserving a `swap` opcode. This diagnostic shows why a hardware-aware second optimization stage is justified; it is not an exact global routing model.

## Controlled Aer Noise Sweep

The new Aer study uses one declared synthetic model:

```text
one-qubit depolarizing error: 1e-4
readout error:              2e-2
two-qubit depolarizing:     varied
shots:                      4096
observable:                 all-Z
circuit:                    deterministic 8-qubit community benchmark
```

| Scenario | 2Q error | Exact <Z...Z> | Aer estimate | Absolute error |
| --- | ---: | ---: | ---: | ---: |
| low | 0.1% | 1.0 | 0.707031 | 0.292969 |
| medium | 0.5% | 1.0 | 0.655762 | 0.344238 |
| high | 1.0% | 1.0 | 0.602051 | 0.397949 |
| severe | 2.0% | 1.0 | 0.490723 | 0.509277 |

The monotonic degradation is expected. Results establish scenario sensitivity only. They do not model QPD reconstruction variance, live-device drift, or a specific QPU.

## Verification

| Check | Result |
| --- | --- |
| K=2 matches established balanced toy objective | PASS |
| K=3 heterogeneous capacity matches exhaustive oracle | PASS |
| K-way infeasibility has no false certificate | PASS |
| Fragment transpilation metrics | PASS |
| Controlled Aer evaluation | PASS |
| Directed log interval test | PASS |
| E9 K=2..5 heterogeneous matrix | `101/144` closed; all 144 return solver-tolerance bounds |
| Lexicographic 5% stage-two probe | `10/12` completed; no improvement witness |
| Focused K/J/H tests | `30 passed in 3.17s` |
| Full repository regression | `131 passed in 23.43s` |
| K-way experiment matrix | `12/12 optimal` |
| Operational joint reconstruction | `8/8 executable legal blocks` |
| FakeBrisbane hardware matrix | `20/20 optimal` |

## Artifacts And Reproduction

```text
results/certicut_k_experiments.json
results/phase10_4c_operational_joint_reconstruction.json
results/certicut_hardware_existing_matrix.json
results/e7_k_heterogeneous_scaling_replicated.jsonl
results/e9_k_heterogeneous_scaling_replicated_summary.json
results/e9_k_symmetry_scaling.jsonl
results/e9_k_strengthening_ablation.jsonl
results/e9_k_kahip_baseline.jsonl
results/e9_k_weighted_heuristic.jsonl
results/e10_algorithmic_kway.jsonl
results/e7_k_lexicographic_routing.json
```

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\run_certicut_k_experiments.py
.\.venv\Scripts\python.exe scripts\run_phase10_4c_operational_study.py
.\.venv\Scripts\python.exe scripts\run_phase10_2_fake_brisbane.py --out results\certicut_hardware_existing_matrix.json
.\.venv\Scripts\python.exe scripts\run_e7_k_scaling.py --seeds 3 --output results\e7_k_heterogeneous_scaling_replicated.jsonl
.\.venv\Scripts\python.exe scripts\summarize_e9_k_replicated.py
.\.venv\Scripts\python.exe scripts\run_e9_k_strengthening_ablation.py
.\.venv\Scripts\python.exe scripts\run_e9_k_weighted_heuristic.py
.\.venv\Scripts\python.exe scripts\run_e10_algorithmic_kway.py
.\.venv\Scripts\python.exe scripts\run_e7_k_lexicographic.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Decision

Primary paper contribution now defensible:

```text
Capacitated K-way independent-QPD circuit partitioning with solver-tolerance
anytime model-overhead bounds.
```

Follow-up contribution already supported, but separate:

```text
Theorem-backed legal K=2 parallel joint-QPD reconstruction and objective optimization.
```

Next technical rung: lexicographic hardware-aware CertiCut-K. Stage one minimizes `log(Gamma)`. Stage two fixes `log(Gamma) <= log(Gamma*) + log(1.05)` then minimizes a routing surrogate. Do not claim exact global mapping, K-way joint QPD, numerical exactness, or QPU prediction until those models are separately formulated and validated.
