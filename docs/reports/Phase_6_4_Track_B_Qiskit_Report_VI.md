# CertiCut Phase 6.4A Qiskit Practical-Qmax Track B Report

Ngày: 11/08/2026

## Trạng thái

PASS. Qiskit automatic gate-cut finder is benchmarked under separate practical-Qmax semantics with explicit search limits, proof-status preservation, and algorithmic Track A overlap detection.

## Qiskit Protocol

```python
OptimizationParameters(
    seed=0,
    gate_lo=True,
    wire_lo=False,
    max_gamma=float("inf"),
    max_backjumps=budget,
)
DeviceConstraints(qubits_per_subcircuit=Qmax)
```

The installed Qiskit Addon Cutting `0.10.0` accepts unrestricted `max_gamma=float("inf")` and `max_backjumps=None`; six n=8 Q-Complete attempts run successfully. Main controlled early-stop budgets are:

```text
max_backjumps = 0, 10, 100
```

No hard wall-clock claim is made. Runtime is actual call duration. `max_gamma` is infinite in every main record, preventing objective-scale censoring for high-overhead QAOA representations.

## Track B Metadata

Each record preserves:

```text
qiskit_seed, max_backjumps, max_gamma
sampling_overhead, objective_log, minimum_reached
gate-cut indices, fragment count/sizes, maximum width
qmax requested, runtime
track_a_overlap
Track A optimum and objective difference only on overlap
```

Gate-only mode rejects any non-gate cut. Every input was already audited to contain operations of arity at most two.

## Matrix

```text
sources: paired MQT QAOA, BV, VQE Real-Amplitudes
representations: CX-normalized, native-QPD
sizes: 8,12,16
Qmax = ceil(n/2)
records: 60
errors: 0
```

## Practical Fragment Semantics

| Result | Count |
| --- | ---: |
| Two balanced fragments, Track A overlap | `37/60` |
| Three fragments | `3/60` |
| Five fragments | `8/60` |
| Seven fragments | `6/60` |
| Nine fragments | `6/60` |

Representation split:

| Representation | Overlap | `minimum_reached=True` |
| --- | ---: | ---: |
| CX-normalized | `17/30` | `12/30` |
| Native-QPD | `20/30` | `12/30` |

Family split shows the specialization gap directly:

```text
QAOA overlap: 17 records
VQE overlap: 20 records
BV overlap: 0 records; Qiskit chooses 5/7/9 fragment schemes
```

Thus exact balanced K=2 is practically relevant for some circuits but not equivalent to Qiskit practical width cutting in general. K=2 remains an explicit CertiCut V1 limitation.

## Overlap Comparison

On the `37` outputs that are exactly two balanced fragments:

```text
Qiskit objective matches Track A CertiCut/MILP optimum: 22
Qiskit objective is higher than Track A optimum: 15
Qiskit overlap outputs with minimum_reached=True: 10
```

Objective differences are reported only on overlap. `minimum_reached=False` is retained as Qiskit proof status; it is not interpreted as a numerical suboptimality gap. CertiCut Track A's quantitative `LB`, `UB`, and factor certificate remain a different information model, not a direct Qiskit-vs-CertiCut runtime ranking.

## Runtime

Actual median call durations:

| Backjump budget | Median runtime |
| --- | ---: |
| `0` | `0.00655s` |
| `10` | `0.01039s` |
| `100` | `0.01600s` |
| `None`, n=8 only | `0.01428s` |

These values are protocol-specific call times, not equal-wall-clock anytime results.

## Files

- `certicut/baselines/qiskit_cut_finder.py`
- `tests/test_baselines.py`
- `scripts/run_phase6_4.py`
- `results/phase6_4_track_b_records.jsonl`
- `results/phase6_4_track_b_summary.json`

## Verification

```text
66 passed in 18.36s
60 Track B records, 0 errors
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase6_4.py
```

## Next

Phase 6.6 must establish isolated-process memory and wall-clock benchmark protocol before final paper-scale claims. General-K remains a scope decision prompted by this Track B fragment-count evidence, not an implicit extension.

`ponytail:` Q-Complete was attempted only at n=8. No unrestricted completion/scalability claim is made for high-cost n=12/16 native-QPD circuits.
