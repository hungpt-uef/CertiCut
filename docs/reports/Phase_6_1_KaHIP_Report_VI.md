# CertiCut Phase 6.1 KaHIP Baseline Report

Ngày: 11/08/2026

## Trạng thái

PASS. KaHIP `3.25` is integrated as an independent Track A exact-balanced graph-partitioning baseline.

## Verified Binding Contract

Installed Windows CPython 3.11 wheel accepts the official nine-argument interface:

```python
edgecut, blocks = kahip.kaffpa(
    vwgt,
    xadj,
    adjcwgt,
    adjncy,
    nblocks,
    imbalance,
    suppress_output,
    seed,
    mode,
)
```

The authoritative five-node CSR example executes successfully against the installed wheel.

## CertiCut Mapping

CNOT-only V1 edge cost:

```text
w_ij = m_ij * log(9)
```

`log(9)` is a common positive constant. KaHIP therefore receives exact objective-equivalent integer edge weights:

```text
adjcwgt = m_ij
```

Every undirected interaction edge is emitted twice in CSR:

```text
u -> v, weight=m_ij
v -> u, weight=m_ij
```

KaHIP `edgecut` is diagnostic only. Reported objective is always recomputed from the original undirected `InteractionGraph`:

```text
J(P) = sum(w_ij for crossed interaction edges)
```

This equivalence is CNOT-only. It must not be generalized to future mixed gate-dependent QPD costs without explicit deterministic scaling protocol.

## Balance Semantics

KaHIP runs:

```text
nblocks = 2
imbalance = 0.0
unit vertex weights
```

Returned block sizes are validated after every call. A partition not matching:

```text
floor(n/2), ceil(n/2)
```

is recorded as `incompatible_balance`; no implicit repair exists.

## Regression

- Official five-node KaHIP CSR example works.
- Six-qubit toy: KaHIP returns `3+3`; recomputed objective is no less than Phase 2 MILP optimum.
- Even `n=8`: exact `4+4` balance.
- Odd `n=9`: exact `4+5` balance.
- Aggregated `3*CX(0,1)`: CSR weights `[3,3]`, recomputed objective `log(729)`.
- Fixed-seed Track A runner produces an independent heuristic record without certificate fields.

## Pilot Integration

Track A pilot now contains:

```text
100 instances
H2, H3, KaHIP-Strong, Phase 2 MILP, CertiCut B2S-R + H2
500 method runs
0 errors
```

Main paper baseline mode is provisionally `KaHIP-Strong`. `FAST`/`ECO` remain available for Phase 6.2 mode-quality/runtime profiling; no mode claim is made yet.

## Files

- `certicut/baselines/kahip.py`
- `certicut/benchmark/runner.py`
- `tests/test_baselines.py`
- `tests/test_benchmark_runner.py`
- `scripts/run_phase6_pilot.py`
- `requirements.txt`
- `results/phase6_pilot_track_a.jsonl`

## Verification

```text
52 passed in 15.52s
500 pilot runs, 0 errors
```

Tái lập:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_phase6_pilot.py
```

## Next

Phase 6.2: deterministic node-budget checkpoint records (`0,1,5,10,30,100`) on hard sizes `24,26,32`; compare H2/H3/KaHIP/MILP/B0 ablations/CertiCut without mixing Track B Qiskit data.

`ponytail:` KaHIP-Strong is an independent feasible-solution baseline, never a lower-bound/proof baseline. Its `edgecut` never enters paper objective tables.
