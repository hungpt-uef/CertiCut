# CertiCut Phase 10.1 Hypergraph, Joint-Cutting, and Hardware-Aware MILP Report

Ngày: 11/08/2026

## Trạng thái

**PARTIAL PASS.** Phase 10.1 establishes and validates a pilot hypergraph-partitioning path: deterministic gate-block aggregation, operator-Schmidt-rank calculation by SVD, unbalanced multi-QPU assignment with capacity constraints, and a reproducible synthetic topology/readout-noise experiment. The exact MILP returns an optimal feasible partition for all `20/20` pilot configurations.

The phase is **not yet a complete implementation** of the requested joint-cutting and hardware-aware objective. Multi-qubit joint blocks, live IBM backend calibration retrieval, gate-error accumulation, and optimization of routing/SWAP cost remain explicitly deferred. The present report separates implemented facts from target-model work still required.

## Implemented Scope

### Hypergraph Pilot Representation

The new hypergraph representation defines:

```text
H = (V, E)
V: logical circuit qubits
E: gate blocks indexed by their common sorted qubit tuple
```

For the pilot, a block consists of all multi-qubit instructions sharing the same endpoint tuple. For each block `B`, the implementation:

1. Extracts its induced subcircuit.
2. Forms the unitary matrix `U_B` with Qiskit `Operator`.
3. Selects a default bipartition: first half of block qubits versus the remainder.
4. Reshapes `U_B` into the operator-bipartite matrix.
5. Computes singular values with NumPy SVD.
6. Counts singular values above `1e-7` to obtain `rank_S(B)`.

The pilot hyperedge record persists:

```text
edge_id
qubits
schmidt_rank
weight
```

For ranks greater than one, the current weight is:

```text
w_e = log(rank_S(B))
```

For a rank-one block, the implementation uses a temporary `0.1` nonzero penalty instead of the literal `log(1)=0`. This is a search-stability surrogate and is not the requested mathematical objective. It must be removed or replaced by a justified physical overhead model before scientific claims about rank-one blocks.

### Schmidt-Rank Validation

The SVD calculation is covered by deterministic unit tests:

| Gate block | Expected operator-Schmidt rank | Result |
| --- | ---: | ---: |
| CX | 2 | PASS |
| iSWAP | 4 | PASS |

These values match the standard operator-Schmidt structure of the tested two-qubit unitaries. The test establishes correct tensor-axis ordering for the current two-qubit pilot path.

### Unbalanced Multi-QPU Assignment MILP

For `n` logical qubits, `K` QPUs, capacities `C_k`, and hyperedges `e`, the implementation creates:

```text
y_i,k in {0,1}: logical qubit i is assigned to QPU k
x_e   in {0,1}: endpoints of hyperedge e occupy more than one QPU
```

The MILP enforces:

```text
sum_k y_i,k = 1                         for every logical qubit i
sum_i y_i,k <= C_k                      for every QPU k
x_e >= y_u,k - y_v,k                    for every ordered endpoint pair (u,v) in e and QPU k
```

The last constraint family correctly forces `x_e=1` when any two endpoints of a represented block receive different QPU assignments. A symmetry condition fixes logical qubit `0` to QPU `0`.

The implemented optimization term is currently:

```text
min sum_e alpha * w_e * x_e
  + sum_i,k gamma * readout_error(i,k) * y_i,k
```

where readout error is optional and comes from the supplied `QPUSpec` fixture. This is a valid unbalanced assignment-and-cut MILP for the represented blocks.

## Hardware and Noise Pilot

`QPUSpec` carries a QPU identifier, capacity, coupling edges, optional two-qubit gate-error mapping, and optional readout-error mapping.

The experiment uses deterministic synthetic line-plus-cross-edge maps intended only as an IBM Heavy-Hex-like topology surrogate. Readout errors are deterministic synthetic values in the range `0.010` to `0.025`. No IBM Runtime, IBM Quantum Platform, `ibm_brisbane`, or `ibm_kyoto` API was queried in this phase.

The routing estimator computes an all-pairs shortest-path distance on the declared coupling graph, then reports a fragment-level average-distance penalty. It is a post-solve diagnostic in this implementation. It is not an exact transpiler SWAP count.

## Pilot Experiment Protocol

### Circuit Families

The experiment evaluates two deterministic circuit families:

| Family | Construction | Sizes |
| --- | --- | --- |
| QAOA-style | nearest-neighbor `RZZ(pi/4)` plus next-nearest `RZZ(pi/3)` layers | 8, 12, 16, 20, 24 |
| VQE Real-Amplitudes | Qiskit Real-Amplitudes ansatz, two repetitions | 8, 12, 16, 20, 24 |

For each circuit, the MILP is solved for `K=2` and `K=3` QPUs. Per-QPU capacity is deliberately unbalanced:

```text
C_k = floor(n / K) + 2
```

This capacity policy permits empty QPUs. Empty QPUs are observed in several `K=3` solutions and are legal under the current unbalanced formulation.

### Objective Weights

```text
alpha = 1.0
beta  = 0.5
gamma = 0.5
```

`alpha` and `gamma` influence the solved MILP. Although `beta` is recorded in the target objective, the present code only evaluates the SWAP surrogate after solving. Therefore `beta` does not yet affect partition selection.

## Results

### Completion and Runtime

All `20/20` pilot configurations terminated with a HiGHS MILP optimum.

| Circuit | n | K | Hyperedges | Cut blocks | MILP time | Objective |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QAOA | 8 | 2 | 10 | 2 | 0.023s | 3.199 |
| QAOA | 8 | 3 | 10 | 2 | 0.034s | 3.456 |
| VQE | 8 | 2 | 7 | 1 | 0.008s | 1.913 |
| VQE | 8 | 3 | 7 | 1 | 0.017s | 2.170 |
| QAOA | 12 | 2 | 16 | 2 | 0.019s | 6.400 |
| QAOA | 12 | 3 | 16 | 2 | 0.020s | 5.879 |
| VQE | 12 | 2 | 11 | 1 | 0.008s | 5.114 |
| VQE | 12 | 3 | 11 | 1 | 0.019s | 4.593 |
| QAOA | 16 | 2 | 22 | 2 | 0.032s | 10.428 |
| QAOA | 16 | 3 | 22 | 4 | 0.157s | 9.249 |
| VQE | 16 | 2 | 15 | 1 | 0.009s | 9.142 |
| VQE | 16 | 3 | 15 | 2 | 0.112s | 6.677 |
| QAOA | 20 | 2 | 28 | 2 | 0.032s | 15.089 |
| QAOA | 20 | 3 | 28 | 4 | 0.286s | 12.441 |
| VQE | 20 | 2 | 19 | 1 | 0.008s | 13.803 |
| VQE | 20 | 3 | 19 | 2 | 0.144s | 9.868 |
| QAOA | 24 | 2 | 34 | 2 | 0.035s | 20.450 |
| QAOA | 24 | 3 | 34 | 4 | 0.347s | 16.715 |
| VQE | 24 | 2 | 23 | 1 | 0.011s | 19.163 |
| VQE | 24 | 3 | 23 | 2 | 0.235s | 14.143 |

Observed solve time ranges from `0.008s` to `0.347s`. Hypergraph construction ranges from `0.002s` at `n=8` to `0.006s` at `n=24`. These times are pilot measurements on deterministic synthetic circuits and are not a general scaling claim.

### Structural Observations

1. QAOA-style circuits produce `10, 16, 22, 28, 34` endpoint blocks from `n=8` through `n=24`; VQE produces `7, 11, 15, 19, 23`.
2. Under `K=2`, QAOA produces two cut blocks at every tested size, while VQE produces one.
3. Under `K=3`, both families can reduce the diagnostic total objective despite increasing the number of cut blocks. For example, QAOA at `n=24` changes from two cuts and objective `20.450` to four cuts and objective `16.715` because the post-solve routing/error diagnostics are lower for the three-fragment layout.
4. This observation is descriptive only. Because SWAP cost is not currently optimized in the MILP, it does not establish that the solver has optimized a joint cutting-routing tradeoff.

### Capacity and Fragment Results

The current unbalanced constraints permit fragment sizes such as:

```text
QAOA, n=24, K=2: [11, 13]
QAOA, n=24, K=3: [7, 7, 10]
VQE,  n=24, K=2: [11, 13]
VQE,  n=24, K=3: [7, 7, 10]
```

For smaller `K=3` cases, an unused QPU is sometimes optimal under the present capacity-only objective. This behavior is expected: the model requires at most `C_k` qubits per QPU but does not require every QPU to receive one qubit. A future exact-`K` mode must add:

```text
sum_i y_i,k >= 1                         for every QPU k
```

## Correctness Coverage

New tests cover:

| Test | Assertion | Result |
| --- | --- | --- |
| Schmidt rank | `rank_S(CX)=2`, `rank_S(iSWAP)=4` | PASS |
| Hypergraph construction | repeated gates aggregate by endpoint tuple | PASS |
| Unbalanced MILP | assignment and capacity constraints hold | PASS |
| Hardware/noise fixture | finite cut, routing, error, total objective values return | PASS |

Regression result:

```text
73 passed in 21.12s
```

## Files

- `certicut/graph/hypergraph.py`
- `certicut/optimization/hypergraph_milp.py`
- `certicut/graph/__init__.py`
- `certicut/optimization/__init__.py`
- `tests/test_hypergraph_milp.py`
- `scripts/run_step1_experiments.py`
- `results/step1_hypergraph_milp_summary.json`

## Reproduction

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest -q tests\test_hypergraph_milp.py
.\.venv\Scripts\python.exe scripts\run_step1_experiments.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Explicit Limitations and Required Next Work

1. **No multi-qubit joint blocks yet.** The grouping key is the exact sorted endpoint tuple. Current benchmark circuits therefore yield two-qubit hyperedges, not true higher-arity hyperedges. `block_strategy` is currently a placeholder and does not alter construction.

2. **Schmidt partition is default-only.** The rank computation uses the first half of a block versus the second half. For a true higher-arity block, partition-aware or minimum-over-bipartitions rank semantics must be specified and tested.

3. **Rank-one weight deviates from target formula.** `log(rank_S(B))` is zero for rank one, but the pilot substitutes `0.1`. Remove this surrogate or formally justify it before comparing objectives.

4. **The MILP minimizes a cut objective, not Max-Cut.** The module name follows the requested wording, but the implemented objective minimizes cut cost. The scientifically accurate label is capacity-constrained minimum hyperedge-cut partitioning.

5. **SWAP cost is not in the MILP.** The routing estimator is computed after optimization and cannot influence the chosen partition. An exact or linearized routing surrogate must be represented by MILP variables/constraints before claiming optimization of the `beta` term.

6. **Gate-error rates are not used.** `QPUSpec.gate_error_rates` is stored but the current solved objective only includes optional readout error. Gate allocation, routing-dependent two-qubit error accumulation, and readout error need one coherent formulation.

7. **No real IBM calibration data.** The pilot uses synthetic coupling and readout-error fixtures. Backend retrieval for `ibm_brisbane` and `ibm_kyoto` requires authenticated IBM Runtime access, a frozen calibration timestamp, and explicit handling of API drift.

8. **No hardware execution or finite-shot validation.** All conclusions concern mathematical optimization under a synthetic topology/noise surrogate, not observed hardware fidelity, total variation distance, or sampling cost.

## Decision

Retain the Phase 10.1 pilot as a validated development rung. Do not merge its objective or results into the CertiCut paper's certified independent-QPD claims. Advance to Phase 10.2 only after implementing true block strategies, mathematically consistent rank-one treatment, and a solver-integrated routing/gate-error objective.

`ponytail:` do not call this joint cutting or IBM hardware-aware optimization in a paper yet. Upgrade only when the listed terms influence the solved decision and are verified against backend-calibration and transpiler evidence.
