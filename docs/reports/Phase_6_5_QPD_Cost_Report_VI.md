# CertiCut Phase 6.5 Gate-Dependent QPD Cost Report

Ngày: 11/08/2026

## Trạng thái

PASS. CertiCut now supports gate-dependent independent QPD sampling costs supplied directly by Qiskit Addon Cutting `0.10.0`.

## Cost Model

Production source of truth:

```python
basis = QPDBasis.from_instruction(operation)
rho_g = basis.overhead
c_g = log(rho_g)
```

Objective:

```text
Gamma(P) = product(rho_g for crossed gates g)
J(P) = log(Gamma(P)) = sum(log(rho_g) for crossed gates g)
```

This is the **independent Qiskit-QPD-0.10.0-compatible gate-cut cost model**. It is not a claim of globally optimal arbitrary-gate or joint-QPD decomposition overhead.

Unsupported, non-two-qubit, and unbound parameterized operations fail fast. There is no fallback to CX cost.

## Registry Validation

| Gate | Qiskit overhead | Analytical regression |
| --- | ---: | ---: |
| CX | `9` | `9` |
| CZ | `9` | `9` |
| CS | `5.828427124746192` | `3+2sqrt(2)` |
| iSWAP | `49` | `49` |
| DCX | `49` | `49` |
| RZZ(0) | `1` | `1` |
| RZZ(pi/4) | `5.828427124746192` | `(1+2|sin(theta)|)^2` |
| RZZ(pi/2) | `9.000000000000004` | `9` |
| RXX(pi/4) | `5.828427124746192` | `(1+2|sin(theta)|)^2` |

Artifact: `results/qpd_cost_registry_validation.json`.

## Graph Generalization

Opt-in graph construction:

```python
build_interaction_graph(circuit, cost_model="qiskit_qpd")
```

Each raw gate occurrence now stores:

```text
gate_params
qpd_overhead
qpd_log_cost
qpd_source
```

Edge aggregate remains mathematically unchanged:

```text
w_ij = sum(qpd_log_cost for gates on edge (i,j))
```

Default `legacy_cx` behavior is unchanged for Phases 0-6.3 reproducibility.

## Sampling-Aware Counterexamples

### Same cut count, different overhead

```text
Plan A: 2 CX cuts -> Gamma=81
Plan B: 2 CS cuts -> Gamma=(3+2sqrt(2))^2 ≈ 33.97
```

Both cut two gates. Mixed-cost exact optimizer chooses Plan B.

### More cuts, lower overhead

```text
Plan A: 2 iSWAP cuts -> Gamma=49^2=2401
Plan B: 3 CX cuts -> Gamma=9^3=729
```

Mixed-cost exact optimizer chooses Plan B. Therefore minimizing cut count is not equivalent to minimizing sampling overhead.

## Correctness Ladder

- Qiskit QPD values match analytical family regressions.
- Mixed CX/RZZ/iSWAP edge aggregation equals direct gate-level objective.
- `100/100` seeded mixed-gate instances: MILP optimum equals brute force.
- `100/100` seeded mixed-gate instances: B2S-R B&B completes with `LB=UB=OPT`.
- `100/100` node-limit-zero mixed instances: `LB <= OPT <= UB`.
- Existing CNOT-only regression suite remains passing.

Metric/cut-polytope B2S remains valid because it constrains partition geometry while all QPD edge weights are nonnegative; only objective coefficients changed.

## KaHIP Scope

KaHIP remains objective-equivalent only in CNOT-only Track A-CX:

```text
w_ij = m_ij * log(9)
```

Gate-dependent real weights require an explicit integer scaling/quantization protocol; KaHIP is intentionally not benchmarked in mixed-QPD mode yet.

## Files

- `certicut/costs/qpd.py`
- `certicut/costs/__init__.py`
- `certicut/graph/interaction.py`
- `tests/test_qpd_costs.py`
- `scripts/validate_qpd_costs.py`
- `results/qpd_cost_registry_validation.json`

## Verification

```text
63 passed in 18.16s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\validate_qpd_costs.py
```

## Next

Phase 6.5B: native logical two-qubit ingestion audit where every gate has Qiskit QPD cost; compare CX-normalized and native-QPD representations on suitable real circuits. Track B Qiskit practical-Qmax remains separate.

`ponytail:` no arbitrary-gate global-overhead claim; Qiskit 0.10 decomposition overheads are the explicit V1 model.
