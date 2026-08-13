# CertiCut Phase 6.0 Benchmark Infrastructure Report

Ngày: 11/08/2026

## Trạng thái

PASS. Track A benchmark engine, immutable instance IDs, unified nullable records, memory capture, and failure-preserving JSONL are implemented and validated on a deterministic pilot.

## Scope

Phase 6.0 is infrastructure validation only. It does not claim method superiority, topology correlation, or paper-scale performance from the easy pilot rung.

## Benchmark Engine

Files:

```text
certicut/benchmark/instance.py
certicut/benchmark/schema.py
certicut/benchmark/runner.py
```

Instance ID:

```text
synthetic/{family}/n{num_qubits}/seed{seed:03d}
```

Each Track A record has a consistent schema:

```text
instance_id, method, track, status, runtime_s
objective_log, sampling_overhead
lb_log, ub_log, log_gap, certified_factor, proven_optimal
num_cuts, fragment_sizes
expanded_nodes, root_time_s, tree_time_s, peak_memory_mb
error
```

Non-applicable data is `null`; heuristic records never invent LB/certificate fields. Exceptions are emitted as `status="error"` records rather than silently dropped.

Peak memory currently records process RSS delta. This is a process-level proxy, suitable for pilot observability; isolated process peak-RSS is required before final paper memory claims.

## Pilot Matrix

```text
Track: A exact balanced K=2
sizes: 8, 12, 16, 20
families: community, nearest-neighbor, QAOA ring, random, dense
seeds: 5
instances: 100
methods: H2, H3, Phase 2 MILP, CertiCut B2S-R + H2
method runs: 400
```

Results:

| Property | Result |
| --- | --- |
| Errors | `0/400` |
| Heuristic feasible runs | `200/200` |
| Phase 2 MILP optimal | `100/100` |
| CertiCut proven optimal | `100/100` |
| Median H2 runtime | `0.000736s` |
| Median H3 runtime | `0.000955s` |
| Median MILP runtime | `0.016400s` |
| Median CertiCut runtime | `0.017582s` |

All pilot CertiCut instances are easy enough to prove under the default complete solve. This validates recording and cross-method execution, but cannot support hard-tail conclusions. Next rung must include `n=24,26,32` and checkpoint/node-budget records.

## KaHIP Status

`kahip==3.25` installed in `.venv` and pinned in `requirements.txt`.

The Windows binding exposes a low-level nine-argument `kaffpa` callable. Its installed docstring does not identify the graph payload or weighted-adjacency argument contract, and direct probes did not match the documented `adjcwgt` style API. No adapter was guessed or silently degraded.

Status:

```text
installed: yes
Track A adapter: blocked pending verified binding contract
benchmark results: none
```

This is a documented compatibility blocker, not an omitted baseline. Phase 6.1 must validate the binding against authoritative source/example or select another independently maintained partitioner with an inspectable Python contract.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase6_pilot.py
```

## Files

- `certicut/benchmark/instance.py`
- `certicut/benchmark/schema.py`
- `certicut/benchmark/runner.py`
- `tests/test_benchmark_runner.py`
- `scripts/run_phase6_pilot.py`
- `results/phase6_pilot_track_a.jsonl`
- `requirements.txt`

## Verification

```text
48 passed in 15.78s
400 pilot runs, 0 errors
```

## Next

1. Phase 6.1: resolve or replace KaHIP binding, validate exact-balance semantics, then add independent baseline.
2. Phase 6.2: add checkpoint/node-budget capture, pilot `n=24,26,32` hard families.
3. Phase 6.3: integrate real quantum-circuit ingestion before paper-scale runs.

`ponytail:` do not scale seeds or method matrix until independent baseline and hard-rung checkpoint schema are complete; a larger easy corpus would increase cost without changing a decision.
