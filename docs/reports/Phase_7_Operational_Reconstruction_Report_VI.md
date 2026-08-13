# CertiCut Phase 7 Operational QPD Reconstruction Report

Ngày: 11/08/2026

## Trạng thái

PASS. CertiCut-selected partitions are operationally executed through Qiskit gate cutting, exact QPD subexperiments, and observable reconstruction.

## Pipeline

```text
Circuit
-> Qiskit-QPD interaction graph
-> exact CertiCut partition
-> selected crossing instruction indices
-> qiskit_addon_cutting.cut_gates
-> partition_problem
-> generate_cutting_experiments(num_samples=inf)
-> ExactSampler
-> reconstruct_expectation_values
-> compare uncut Statevector observable
```

The bridge asserts that solution cut indices exactly match the graph partition's crossed raw gate metadata before execution. This prevents graph/circuit plan mismatch.

## Exact Results

Observable: global `Z...Z` expectation.

| Circuit | Representation | Partition | Cut indices | Optimizer Gamma | QPD Gamma | Exact error | Experiments/fragment |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| QAOA n=6 | native RZZ(pi/4) | `{0,1,5}` / `{2,3,4}` | `13,16` | `33.97056274847716` | same | `1.39e-17` | `36,36` |
| VQE n=6 | CX | `{0,1,2}` / `{3,4,5}` | `8` | `9.000000000000002` | same | `5.55e-17` | `6,6` |

For both circuits:

```text
optimizer J(P) = sum(log(QPDBasis.overhead)) of operational cut gates
exp(J(P)) = actual QPD product overhead
reconstructed expectation = uncut statevector expectation within 1e-10
```

## Scope

Execution uses exact quasiprobability evaluation (`num_samples=inf`) and `ExactSampler`. It validates operational plan compatibility and reconstruction correctness, not finite-shot estimator variance. No claim is made that observed finite-shot variance equals the QPD overhead exactly.

Finite-shot repetitions are deferred: the QAOA native plan already produces 36 experiments per fragment under exact QPD decomposition, and a statistically meaningful variance study would be a separate sampling experiment rather than required operational proof.

## Files

- `certicut/qiskit_bridge/operational.py`
- `tests/test_operational_reconstruction.py`
- `scripts/run_phase7.py`
- `results/phase7_operational_validation.json`

## Verification

```text
69 passed
2/2 operational plans executed
2/2 exact reconstructions within 1e-10
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase7.py
```

## Decision

Stop algorithm feature development. Core optimizer, cost model, external baselines, final benchmarks, and executable QPD plan validation are complete. Next work is Phase 8 statistics, figures, tables, and paper writing.

`ponytail:` finite-shot QPD variance is not required for V1 operational validation; add only as a separately replicated statistical study, never as a one-run demonstration.
