# CertiCut Phase 10.2 Solver-Integrated Joint-Cutting and Hardware-Aware MILP Report

Ngày: 11/08/2026

## Trạng thái

**FULL PASS (offline FakeBackend hardware-aware Schmidt-surrogate benchmark).** Phase 10.2 removes the rank-one penalty surrogate, creates true temporal-spatial joint blocks, computes partition-aware operator-Schmidt surrogate costs, and integrates physical placement, routing, readout error, and two-qubit gate error directly into the HiGHS MILP objective. A frozen calibration snapshot from the official Qiskit IBM Runtime `FakeBrisbane` provider supplies a 127-qubit Heavy-Hex-derived offline topology and error data. The `20/20` configured FakeBrisbane matrix completes with exact HiGHS optima; every configuration contains at least one hyperedge covering three qubits.

This status applies only to the stated **offline FakeBackend calibration benchmark**. It does not claim live IBM execution, contemporaneous device calibration, noisy reconstruction, finite-shot validation, hardware fidelity, or executable/optimal joint-QPD overhead. Phase 10.3 establishes that the Schmidt term is a surrogate only.

## Delivered Model

### Exact Rank-One Cost

Phase 10.1 assigned a temporary `0.1` penalty to rank-one blocks. That surrogate is removed.

```text
w_e = log(rank_S(B_e))
rank_S(B_e) = 1  =>  w_e = 0
```

The new regression test uses `RZZ(0)`, verifies `rank_S=1`, and verifies `weight=0.0` exactly. No constant penalty remains in the hypergraph module.

### Temporal-Spatial Joint Blocks

`build_hypergraph()` now supports two explicit strategies:

```text
qubit_pair:
  aggregate all instructions with the same sorted endpoint tuple

temporal_spatial:
  scan multi-qubit instructions in circuit order;
  merge a gate into a recent block when:
    1. its support overlaps the block support,
    2. the layer gap is <= depth_window,
    3. merged support cardinality <= max_block_qubits.
```

The Phase 10.2 runner uses:

```text
block_strategy = temporal_spatial
depth_window = 2
max_block_qubits = 3
```

This produces true hyperedges over three logical qubits. A deterministic test with consecutive `iSWAP(0,1)` and `iSWAP(1,2)` produces:

```text
hyperedge support: (0,1,2)
operator-Schmidt rank: 4
rank > 2: PASS
```

### Partition-Aware Schmidt Lookup

For each block `B_e` with support `V_e`, the implementation enumerates all unique nontrivial bipartitions using a fixed anchor qubit to avoid complementary duplicates. For each partition `A | V_e \ A`, it:

1. Extracts the induced block subcircuit.
2. Forms its Qiskit `Operator` matrix.
3. Reshapes the operator into the bipartite tensor matrix.
4. Counts SVD singular values above `1e-7`.
5. Stores `log(rank_S(B_e, A))`.

For a joint assignment pattern `pi_e` over `K` QPUs, the solver selects exactly one pattern variable. If the block spans more than one QPU, its joint cost is the symmetric sum of one-QPU-versus-rest log ranks divided by two:

```text
C_joint(e, pi_e) = 0.5 * sum_{nonempty QPU groups A in pi_e} log(rank_S(B_e, A))
```

For `K=2`, this reduces exactly to the selected bipartition log rank. The formulation is deliberately restricted to blocks of arity at most three because assignment-pattern enumeration grows as `K^|V_e|`.

## Solver-Integrated Hardware-Aware MILP

### Variables

```text
y_i,k in {0,1}
  logical qubit i is assigned to QPU k

z_i,k,u in {0,1}
  logical qubit i is physically placed at site u of QPU k

h_e,pi in {0,1}
  hyperedge e uses QPU assignment pattern pi

x_e in {0,1}
  hyperedge e occupies more than one QPU

p_g,k,u,v in {0,1}
  endpoints of logical gate occurrence g are placed at physical sites u,v of QPU k
```

### Constraints

```text
sum_k y_i,k = 1
  one QPU per logical qubit

sum_i y_i,k <= C_k
  QPU logical capacity

sum_u z_i,k,u = y_i,k
  QPU assignment and physical placement are consistent

sum_i z_i,k,u <= 1
  one logical qubit per physical site

sum_pi h_e,pi = 1
sum_{pi: pi[i]=k} h_e,pi = y_i,k
  exact joint-block assignment pattern

x_e = sum_{pi: |set(pi)|>1} h_e,pi
  exact hyperedge-cut indicator

p_g,k,u,v = z_a,k,u AND z_b,k,v
  linearized through three standard binary-product inequalities
```

The optional `require_nonempty_qpus=True` mode adds `sum_i y_i,k >= 1` for every QPU. Phase 10.2 uses this mode; unlike Phase 10.1, no QPU may remain unused in a declared `K`-QPU experiment.

### Objective

The solved objective is now:

```text
J = alpha * sum_e,pi C_joint(e,pi) * h_e,pi
  + beta  * sum_g,k,u,v multiplicity(g) * max(D_k(u,v)-1,0) * p_g,k,u,v
  + gamma * sum_i,k,u ReadoutErr_k(u) * z_i,k,u
  + delta * sum_g,k,u,v multiplicity(g) * RoutedGateErr_k(u,v) * p_g,k,u,v
```

`D_k(u,v)` is the all-pairs shortest-path distance in the frozen coupling graph of QPU `k`. `RoutedGateErr_k(u,v)` uses the calibrated direct two-qubit error at distance one and a stated three-SWAP-plus-gate surrogate at greater finite distance. Hence `beta`, `gamma`, and `delta` alter coefficients seen by HiGHS before optimization, not post-solve diagnostics.

## Hardware Calibration Freeze Path

The repository now includes a calibration exporter with two explicit sources:

1. `--source fake` (default): instantiates an official Qiskit IBM Runtime FakeProvider backend locally, without a token or network access.
2. `--source live`: requires `QISKIT_IBM_TOKEN`, then retrieves a live backend target through IBM Runtime.
3. Both sources export physical qubits, coupling edges, measurement errors, and available two-qubit instruction errors.
4. Both write a timestamped immutable JSON snapshot with SHA-256 digest.
5. The loader rechecks SHA-256 before constructing a `QPUSpec`.

Live credential guard result:

```text
QISKIT_IBM_TOKEN is required for --source live; no calibration fixture was written.
```

Offline official calibration result:

```text
backend: fake_brisbane
source: qiskit_ibm_runtime_fake_provider
physical sites: 127
coupling edges: 144
readout calibrations: 127
two-qubit calibrations: 144
SHA-256: e694bcbfd96fd71c25f0433b0f4cf79c2312203764fc2ec79197e20b01019a2c
```

The snapshot source is preserved in every experimental record. It is a fixed Qiskit FakeProvider calibration, not a live `ibm_brisbane` service query.

## Offline FakeBrisbane Acceptance Protocol

### Fixture Scope

The initial development rung used deterministic synthetic fixtures. The accepted Phase 10.2 matrix instead uses the frozen official FakeBrisbane snapshot above. To control exact-placement MILP growth, each logical QPU receives a deterministic candidate-site subset selected by BFS from the frozen Heavy-Hex coupling graph:

```text
candidate policy: BFS connected subgraph
candidate count: logical QPU capacity C_k
seed site: QPU identifier k
topology/error source: frozen official FakeBrisbane snapshot
```

Candidate pruning is a solver policy, not a modification of the frozen calibration data. The full 127-site snapshot and SHA-256 remain attached to each record. This benchmark validates offline calibration-aware optimization; it is not hardware-performance evidence.

### Circuits and Solver Settings

| Item | Value |
| --- | --- |
| Families | QAOA-style `RZZ` layers; VQE Real-Amplitudes |
| Sizes | `n in {6, 8, 10, 12, 14}` |
| QPUs | `K in {2, 3}` |
| Hypergraph strategy | temporal-spatial; window `2`; max arity `3` |
| Objective weights | `alpha=1.0`, `beta=0.5`, `gamma=0.5`, `delta=0.5` |
| QPU occupancy | exact nonempty `K` mode |
| Solver | SciPy/HiGHS MILP |

The exact placement model is computationally expensive on QAOA-style `n=14` circuits. The completed matrix uses an extended timeout and reports the observed tail directly rather than omitting it.

## Results

All `20/20` FakeBrisbane configurations returned an exact MILP optimum.

| Circuit | n | K | Hyperedges | Arity >=3 | Cut blocks | Objective | Routing | Readout | Gate error | Solve time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| QAOA-style | 6 | 2 | 3 | 3 | 2 | 1.46941 | 0.0 | 0.1443 | 0.0219 | 0.064s |
| QAOA-style | 6 | 3 | 3 | 3 | 3 | 2.16641 | 0.0 | 0.1594 | 0.0145 | 0.073s |
| VQE | 6 | 2 | 3 | 2 | 1 | 0.78052 | 0.0 | 0.1443 | 0.0305 | 0.052s |
| VQE | 6 | 3 | 3 | 2 | 2 | 1.47698 | 0.0 | 0.1594 | 0.0219 | 0.037s |
| QAOA-style | 8 | 2 | 4 | 4 | 1 | 1.82992 | 2.0 | 0.1709 | 0.1026 | 1.260s |
| QAOA-style | 8 | 3 | 4 | 4 | 3 | 2.18568 | 0.0 | 0.1824 | 0.0301 | 1.419s |
| VQE | 8 | 2 | 4 | 3 | 1 | 0.80162 | 0.0 | 0.1709 | 0.0460 | 0.192s |
| VQE | 8 | 3 | 4 | 3 | 2 | 1.49808 | 0.0 | 0.1860 | 0.0375 | 0.388s |
| QAOA-style | 10 | 2 | 5 | 5 | 1 | 2.37740 | 3.0 | 0.2117 | 0.1568 | 3.081s |
| QAOA-style | 10 | 3 | 5 | 5 | 2 | 2.54748 | 2.0 | 0.2126 | 0.1097 | 9.490s |
| VQE | 10 | 2 | 5 | 4 | 1 | 0.83495 | 0.0 | 0.2117 | 0.0719 | 0.324s |
| VQE | 10 | 3 | 5 | 4 | 2 | 1.51918 | 0.0 | 0.2126 | 0.0531 | 1.273s |
| QAOA-style | 12 | 2 | 6 | 6 | 1 | 2.92487 | 4.0 | 0.2524 | 0.2110 | 33.887s |
| QAOA-style | 12 | 3 | 6 | 6 | 2 | 3.10228 | 3.0 | 0.2678 | 0.1641 | 21.528s |
| VQE | 12 | 2 | 6 | 5 | 1 | 0.86828 | 0.0 | 0.2524 | 0.0978 | 0.554s |
| VQE | 12 | 3 | 6 | 5 | 2 | 1.55983 | 0.0 | 0.2678 | 0.0792 | 0.661s |
| QAOA-style | 14 | 2 | 7 | 7 | 1 | 3.47330 | 5.0 | 0.3091 | 0.2512 | 141.793s |
| QAOA-style | 14 | 3 | 7 | 7 | 2 | 3.64975 | 4.0 | 0.3086 | 0.2183 | 274.919s |
| VQE | 14 | 2 | 7 | 6 | 1 | 0.91295 | 0.0 | 0.3091 | 0.1305 | 1.520s |
| VQE | 14 | 3 | 7 | 6 | 2 | 1.59316 | 0.0 | 0.3086 | 0.1051 | 0.929s |

Observations:

1. Every configuration has at least one true three-qubit hyperedge.
2. Every result contains physical placements, not merely QPU labels, derived from the frozen FakeBrisbane calibration.
3. Gate error is nonzero in `20/20` runs; routing penalty is nonzero in `7/20` runs.
4. Exact placement scales unevenly: VQE remains below `1.6s`; QAOA reaches `141.793s` for `n=14,K=2` and `274.919s` for `n=14,K=3`. This is an observed formulation boundary, not an asymptotic claim.

## Solver Trade-off Sensitivity

A dedicated four-qubit probe uses two QPUs with unequal two-qubit error rates:

```text
QPU 0 direct gate error: 0.5
QPU 1 direct gate error: 0.001
alpha=0.01, beta=0, gamma=0
```

| delta | Partition | Physical placements |
| ---: | --- | --- |
| 0 | `(0,0,1,1)` | `((0,1),(0,0),(1,0),(1,1))` |
| 10 | `(0,1,0,1)` | `((0,1),(1,1),(0,0),(1,0))` |

The partition and placement change when `delta` changes; the hardware-error term therefore affects the actual MILP decision.

A distinct routing-conflict probe verifies `beta` sensitivity:

| beta | Physical placement | Routing cost |
| ---: | --- | ---: |
| 0 | `((0,1),(0,3),(0,0),(0,2))` | 3 |
| 1 | `((0,2),(0,0),(0,1),(0,3))` | 1 |

The routing coefficient changes the chosen placement and lowers solver-integrated routing cost from `3` to `1`.

## Verification

| Check | Result |
| --- | --- |
| Rank-one exact weight | PASS |
| True arity-three joint block | PASS |
| Partition-aware SVD lookup | PASS |
| Placement uniqueness and QPU consistency | PASS |
| Gate-error solver sensitivity | PASS |
| Snapshot SHA-256 validation | PASS |
| Official FakeBrisbane snapshot | PASS; 127 sites, 144 coupling edges, SHA-256 verified |
| FakeBrisbane matrix | `20/20 optimal`; all runs contain arity-three hyperedges |
| Beta routing sensitivity | PASS; placement changes, routing `3 -> 1` |
| Phase 10.2 test module | `11 passed in 1.28s` |
| Full regression suite | `80 passed in 21.54s` |

## Files

- `certicut/graph/hypergraph.py`
- `certicut/optimization/hypergraph_milp.py`
- `certicut/hardware/calibration.py`
- `certicut/hardware/__init__.py`
- `scripts/fetch_ibm_calibration.py`
- `scripts/run_step2_experiments.py`
- `scripts/run_phase10_2_fake_brisbane.py`
- `tests/test_hypergraph_milp.py`
- `results/phase10_2_hardware_aware_joint_summary.json`
- `results/phase10_2_fake_brisbane_matrix.json`
- `fixtures/ibm_brisbane_fake_calib_20260811T075124.json`

## Reproduction

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest -q tests\test_hypergraph_milp.py
.\.venv\Scripts\python.exe scripts\fetch_ibm_calibration.py --backend ibm_brisbane --source fake
.\.venv\Scripts\python.exe scripts\run_phase10_2_fake_brisbane.py
.\.venv\Scripts\python.exe -m pytest -q
```

Optional live calibration freeze, intentionally separate from the offline benchmark:

```powershell
$env:QISKIT_IBM_TOKEN="<IBM Quantum API token>"
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\fetch_ibm_calibration.py --backend ibm_brisbane
```

## Remaining Scope Limits

1. **Offline calibration only.** FakeBrisbane is official fixed backend data, not a contemporaneous query of a live IBM processor.
2. **Exact placement scale boundary.** The current all-pairs exact placement linearization reaches `274.919s` on QAOA-style `n=14,K=3`. Candidate-site pruning is necessary but not a substitute for decomposition at E7--E9 scale.
3. **Joint cost semantics need operational validation.** The symmetric multi-QPU cost is mathematically explicit but has not been verified against executable joint-QPD reconstruction.
4. **No noisy execution result yet.** `AerSimulator.from_backend(FakeBrisbane())` is available offline, but finite-shot joint-cut reconstruction is a separate E9 experiment and is not claimed here.

## Decision

Phase 10.2 is **FULL PASS for the declared offline FakeBackend hardware-aware Schmidt-surrogate benchmark**. It supersedes the Phase 10.1 post-solve SWAP/readout diagnostic: all stated hardware-aware terms now participate in the solved MILP, a SHA-verified official FakeBrisbane snapshot is frozen, the `20/20` matrix is complete, and both `beta` and `delta` sensitivity are demonstrated.

`ponytail:` paper wording may state “offline hardware-calibration-aware optimization using operator-Schmidt surrogate costs and an official Qiskit FakeBrisbane snapshot.” Do not state joint-QPD cost, live IBM execution, device fidelity, or joint-QPD reconstruction until a legal decomposition oracle and executable reconstruction study exist.
