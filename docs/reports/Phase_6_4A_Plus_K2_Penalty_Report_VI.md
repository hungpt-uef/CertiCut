# CertiCut Phase 6.4A+ K=2 Restriction-Penalty Report

Ngày: 11/08/2026

## Trạng thái

PASS. Existing Track B data verifies the overlap/proof invariant and finds no observed sampling-overhead penalty from the exact balanced K=2 specialization on Qiskit-proven practical instances in this first matrix.

## Invariant

Track A exact balanced solutions are feasible under Track B practical width constraint when:

```text
Qmax = ceil(n/2)
```

For a Qiskit result in Track A overlap:

```text
two fragments
sizes floor(n/2), ceil(n/2)
```

the result is feasible in both spaces, so:

```text
J_Qiskit >= OPT_A
```

If Qiskit additionally reports `minimum_reached=True`, then:

```text
OPT_B <= OPT_A <= J_Qiskit = OPT_B
```

and therefore `J_Qiskit=OPT_A=OPT_B` within tolerance.

Result:

```text
overlap + Qiskit-proven records: 10
invariant violations: 0
exact objective matches: 10/10
```

## Restriction Penalty

For every Qiskit `minimum_reached=True` record:

```text
Delta_K2 = OPT_A - OPT_B
F_K2 = exp(Delta_K2)
```

Track A optimum comes from Phase 6.5B MILP under the same source/representation and Qiskit-compatible independent QPD cost model.

| Metric | Result |
| --- | ---: |
| Qiskit-proven practical records | `24` |
| Proven non-overlap records | `14` |
| `F_K2=1` within tolerance | `24/24` |
| Median `F_K2` | `1.0x` |
| p90 `F_K2` | `1.0x` |
| Maximum `F_K2` | `1.000000000000007x` |
| Positive penalty records | `0` |

By family:

```text
BV:  14/14 F_K2=1, despite Qiskit using 5/7/9 fragments
QAOA: 2/2 F_K2=1
VQE: 8/8 F_K2=1
```

## Decision

The observed fragment-count semantic gap does not create a measurable sampling-overhead penalty on this small Qiskit-proven matrix. Do not implement general-K solely because Track B often returns more than two fragments.

Scope remains narrow:

```text
24 Qiskit-proven records
paired QAOA/BV/VQE sources
n=8,12,16
specified Qiskit 0.10 independent-QPD model
```

This does not prove K=2 is penalty-free generally. It does provide evidence that the BV multi-fragment behavior in Phase 6.4A is semantic/component structure rather than an observed overhead disadvantage.

## Files

- `scripts/analyze_phase6_4_restriction.py`
- `results/phase6_4_k2_penalty_records.jsonl`
- `results/phase6_4_k2_penalty_summary.json`

## Reproduction

```powershell
.\.venv\Scripts\python.exe scripts\analyze_phase6_4_restriction.py
```

`ponytail:` phase 6.7 general-K is deferred, not cancelled. Reopen only if broader practical-Qmax proven records exhibit material `F_K2>1` penalty.
