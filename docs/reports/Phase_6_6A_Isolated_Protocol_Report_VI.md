# CertiCut Phase 6.6A Isolated Runtime and Memory Protocol Report

Ngày: 11/08/2026

## Trạng thái

PASS. Fresh-process measurement, peak working-set capture, inclusive wall-clock timeline, and safe time-limit certificates are validated before final benchmark-scale claims.

## Measurement Protocol

Each method run uses a fresh worker process.

```text
process_wall_time_s:
  parent spawn -> worker exit/IPC

algorithm_runtime_s:
  worker builds graph -> H2 -> root LP/separation -> B&B return

peak_rss_mb:
  worker Windows peak working set (psutil peak_wset)

includes_children:
  false
```

Main solver tables should use `algorithm_runtime_s`. System/reproducibility material may report process wall time separately. Worker startup/import/IPC are never silently mixed into algorithm time.

## Inclusive Anytime Clock

The algorithm timer starts before:

```text
H2 warm start
root base LP
root triangle-separation rounds
B&B tree search
```

Root separation now receives remaining budget and returns only at completed LP-round safe boundaries. A time-limit result after root processing carries an incumbent UB and valid current LP lower bound. Each returned certificate satisfies:

```text
LB <= OPT <= UB
```

`budget_s` is a requested soft deadline. Because interruption occurs only at safe LP/node boundaries, actual algorithm runtime can exceed it by one completed operation. Final paper must report actual runtime and not call this hard real-time termination.

## Pilot

```text
families: random, dense, weighted-random
sizes: 24,26
seeds: 3
requested budgets: 0.5s, 1s, 5s
isolated records: 54
```

| Status | Count |
| --- | ---: |
| Optimal | `43` |
| Safe time-limit certificate | `11` |
| Worker error | `0` |
| Missing returned certificate | `0` |

| Requested budget | Median algorithm time | Median process wall time | Median peak working set |
| ---: | ---: | ---: | ---: |
| 0.5s | `0.515s` | `1.540s` | `115.188 MB` |
| 1.0s | `0.517s` | `1.622s` | `115.182 MB` |
| 5.0s | `0.521s` | `1.565s` | `115.622 MB` |

Maximum observed safe-boundary return times:

```text
0.5s requested -> 0.714s actual
1.0s requested -> 1.063s actual
5.0s requested -> 2.318s actual
```

All 54 returned certificates satisfy ordered bounds. No child processes are spawned by the protocol.

## Files

- `certicut/benchmark/isolated.py`
- `tests/test_isolated_benchmark.py`
- `scripts/run_phase6_6a.py`
- `results/phase6_6a_isolated_records.jsonl`

## Verification

```text
67 passed in 21.65s
54 isolated runs
11 safe time-limit certificates
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase6_6a.py
```

## Decision

Phase 6.6B may now use isolated process peak working set and separate algorithm/process time columns. It must label time budgets as safe-boundary requested deadlines and always report actual return time.

`ponytail:` no process kill is used for CertiCut algorithm timeout, because it would discard the valid in-memory certificate. Qiskit hard-deadline experiments remain separate: a killed `find_cuts()` call has no documented returned incumbent.
