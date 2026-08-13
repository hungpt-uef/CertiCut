# CertiCut Phase 5 Baseline Integration Report

Ngày: 11/08/2026

## Trạng thái

PASS integration. Baseline tracks, schema, and Qiskit gate-only sanity are implemented. This phase establishes fair benchmarking protocol; it does not make broad performance claims from one toy circuit.

## Paper Scope

V1 working title:

```text
CertiCut: Certified Anytime Optimization for Sampling-Aware Quantum Circuit Cutting via Polyhedral Relaxations
```

Learning/GNN is locked as future work. Strong-branching artifacts remain stored, but Phase 4 did not justify learning-guided branching in V1.

## Fair Benchmark Tracks

### Track A: Exact Balanced K=2

```text
exactly two non-empty fragments
Qmax = ceil(n/2)
same weighted graph objective
```

Applicable methods:

- CertiCut B2S-R + H2.
- Phase 2 exact MILP oracle.
- H2 graph heuristic.
- H3 spectral plus pair-swap graph heuristic.

Track A supports direct objective/partition-quality comparison. Graph heuristics have no quantitative LB/certificate.

### Track B: Practical Qmax Gate Cutting

```text
maximum subcircuit width Qmax
gate-only QPD cuts
not exact balanced K=2
```

Applicable external method: Qiskit automatic cut finder. Track B is deliberately not used to claim direct optimum ranking against Track A because feasible spaces differ.

## Qiskit Adapter

Environment:

```text
qiskit-addon-cutting == 0.10.0
```

Adapter invokes:

```python
find_cuts(
    circuit,
    OptimizationParameters(
        seed=0,
        gate_lo=True,
        wire_lo=False,
        max_backjumps=None,
        max_gamma=1e12,
    ),
    DeviceConstraints(qubits_per_subcircuit=Qmax),
)
```

The adapter fails if Qiskit returns a non-gate cut. It logs `sampling_overhead`, log-domain objective, gate instruction indices, derived connected-component sizes, and `minimum_reached`. The latter is proof-status only, not a quantitative gap.

## Toy Sanity

Six-qubit Phase 0 circuit, `Qmax=3`:

| Method/Track | Gate cuts | Overhead | Log objective | Fragments | Proof |
| --- | --- | ---: | ---: | --- | --- |
| CertiCut / A | `4,5` | `81` | `log(81)` | `3+3` | factor `1.0x` |
| Phase 2 MILP / A | `4,5` | `81` | `log(81)` | `3+3` | exact solve |
| H2 / A | `4,5` | `81` | `log(81)` | `3+3` | none |
| H3 / A | `4,5` | `81` | `log(81)` | `3+3` | none |
| Qiskit gate-only / B | `4,5` | `81` | `log(81)` | `3+3` | `minimum_reached=True` |

Qiskit gate-only cost matches the V1 independent-CNOT convention:

```text
2 cuts -> 9^2 = 81
log Gamma = log(81)
```

This is an integration sanity check, not evidence the two solvers optimize equivalent feasible spaces generally.

## Files

- `certicut/baselines/common.py`: result schema and safe log-domain overhead conversion.
- `certicut/baselines/graph_heuristics.py`: Track A H2/H3 adapters.
- `certicut/baselines/qiskit_cut_finder.py`: Track B Qiskit gate-only adapter.
- `tests/test_baselines.py`: Track A and Qiskit toy regressions.
- `scripts/run_phase5.py`: deterministic baseline sanity artifact.
- `results/phase5_baseline_sanity.json`.

## Verification

```text
46 passed in 15.66s
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase5.py
```

## Next

Phase 6: benchmark runners across topology/quantum circuit families, scale ladder, checkpoint certificates, and separate Track A/B result tables. Add full classical independent balanced-bisection baseline before paper-scale Track A claims.

`ponytail:` Qiskit runtime benchmark is not yet implemented; documented knobs are `max_backjumps`/`max_gamma`, not a native wall-clock budget. Do not manufacture time-budget claims without subprocess isolation or an explicit protocol.
