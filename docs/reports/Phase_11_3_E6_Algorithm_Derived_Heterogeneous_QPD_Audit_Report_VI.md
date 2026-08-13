# CertiCut E6 Algorithm-Derived Heterogeneous-QPD Audit Report

Ngày: 12/08/2026

## Trạng thái

**E6_FULL_RELEVANCE_PASS.** Audit khóa trước sáu algorithm-derived MQT Bench families, sáu sizes, algorithm-semantic two-qubit representation, và exhaustive balanced enumeration. Cả 36/36 circuits đủ eligibility; 6/36 strict reversals xuất hiện trong hai families. Không có unsupported 2q operation, không có unit-overhead 2q operation, không transpile sang CX hay hardware basis.

Kết quả trả lời câu hỏi relevance theo hướng hẹp nhưng trực tiếp:

```text
heterogeneous independent-QPD costs can change an exact balanced partition
on predeclared algorithm-derived circuit families.
```

Không được diễn giải là prevalence claim cho arbitrary workloads hoặc hardware-routed circuits.

## Frozen Protocol

```text
families:
  draper_qft_adder
  hhl
  qpeexact
  qpeinexact
  qft
  qftentangled

sizes: 6, 8, 10, 12, 14, 16
records: 36

stack:
  Qiskit 2.5.1
  MQT Bench 2.2.2
  Qiskit Addon Cutting 0.10.0

representation_policy: algorithm_semantic_2q_preserving
```

Representation procedure:

1. Generate directly from official MQT algorithm factory.
2. Preserve every generated numeric 1q/2q instruction.
3. Selectively decompose only instructions with arity greater than two.
4. Ignore measurement, barrier, delay during interaction construction.
5. Reject remaining non-1q/2q operations, unbound parameters, unsupported QPD operations, invalid QPD overheads.
6. Query each retained 2q occurrence through `QPDBasis.from_instruction(op).overhead`.

Explicit exclusions:

```text
no qc.decompose(reps=...)
no transpile(..., basis_gates=[cx, rz, sx])
no hardware-native transpilation
no CP/RZZ/CRY rewrite into CX sandwiches
no hand-coded CP/RZZ/CRY QPD formula
```

Main eligibility was predeclared:

```text
no unsupported 2q
AND no unit-overhead 2q
AND at least two distinct positive QPD log-cost classes
```

## Exact Objective

For every positive-cost 2q occurrence `g`, the QPD edge contribution is `log(rho_g)`, where `rho_g` is the Qiskit-provided independent-QPD overhead. The count objective assigns one unit per retained positive-cost 2q occurrence.

For a balanced bipartition `P`:

```text
c(P) = crossed 2q occurrence count
J(P) = sum_{g crossed by P} log(rho_g)
```

The reported count plan is tie-safe:

```text
c*          = min_P c(P)
J_count*    = min_{P: c(P)=c*} J(P)
J_QPD*      = min_P J(P)
strict      = J_count* - J_QPD* > 1e-10
factor      = exp(J_count* - J_QPD*)
```

Qubit 0 is fixed to one side to remove complementary-label symmetry. Thus each `n` uses exactly `C(n-1, n/2-1)` exhaustive partitions: 10, 35, 126, 462, 1,716, and 6,435 for `n=6,8,10,12,14,16` respectively. Every artifact record met this count exactly.

## Eligibility Screen

| Family | Records | 2q range | Positive QPD-cost classes | Retained algorithm-semantic 2q gates | Eligible | Strict reversals |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Draper QFT adder | 6 | 12-92 | 3-8 | CP | 6/6 | 4 |
| HHL | 6 | 28-238 | 10-30 | CP, CRY, SWAP | 6/6 | 0 |
| QPE exact | 6 | 16-127 | 7-29 | CP, SWAP | 6/6 | 2 |
| QPE inexact | 6 | 17-127 | 9-28 | CP, SWAP | 6/6 | 0 |
| QFT | 6 | 18-128 | 6-16 | CP, SWAP | 6/6 | 0 |
| Entangled QFT | 6 | 23-143 | 7-17 | CP, CX, SWAP | 6/6 | 0 |
| **Total** | **36** | **12-238** | **3-30** |  | **36/36** | **6** |

Screening found:

```text
unsupported final 2q operations: 0 / 36 records
unit-overhead final 2q operations: 0 / 36 records
ineligible records: 0 / 36 records
```

This makes every strict reversal identity-free under the frozen E6 rule; none is caused by accepting a zero/unit-cost gate.

## Strict Reversals

| Family | n | c* | J_count* | J_QPD* | Regret log | Factor | Extra cuts at QPD optimum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Draper QFT adder | 10 | 15 | 19.444616 | 16.433576 | 3.011040 | 20.3085x | 2 |
| Draper QFT adder | 12 | 21 | 25.403831 | 20.233713 | 5.170118 | 175.936x | 2 |
| Draper QFT adder | 14 | 28 | 31.617679 | 21.310306 | 10.307373 | 29,952.6x | 6 |
| Draper QFT adder | 16 | 36 | 37.968133 | 24.111328 | 13.856805 | 1,042,158.98x | 6 |
| QPE exact | 6 | 8 | 12.302910 | 12.213352 | 0.089558 | 1.09369x | 1 |
| QPE exact | 14 | 46 | 29.583609 | 28.190012 | 1.393597 | 4.02932x | 1 |

The remaining 30 eligible records are negative results: their tie-safe minimum-count partition already attains `J_QPD*`.

## Mechanism

Draper QFT adder gives the clearest repeated mechanism. At `n=16`, the QPD optimizer takes six additional unit-count cuts but reduces log objective by `13.856805`, a `1.042e6x` independent-QPD factor relative to the best minimum-count plan. It exchanges high-cost `CP(pi/2)` and `CP(pi)` crossings for more small-angle CP crossings. The complete nonzero gate-class accounting below reproduces both exact deltas.

| Draper n=16 gate class | rho | Count-opt cut | QPD-opt cut | Delta QPD minus count |
| --- | ---: | ---: | ---: | ---: |
| CP(-pi/64) | 1.100574 | 1 | 2 | +1 |
| CP(-pi/32) | 1.205901 | 1 | 3 | +2 |
| CP(-pi/16) | 1.430498 | 1 | 3 | +2 |
| CP(-pi/8) | 1.932602 | 1 | 3 | +2 |
| CP(-pi/4) | 3.116520 | 1 | 2 | +1 |
| CP(pi/64) | 1.100574 | 1 | 4 | +3 |
| CP(pi/32) | 1.205901 | 2 | 6 | +4 |
| CP(pi/16) | 1.430498 | 3 | 5 | +2 |
| CP(pi/4) | 3.116520 | 5 | 2 | -3 |
| CP(pi/2) | 5.828427 | 6 | 2 | -4 |
| CP(pi) | 9.000000 | 6 | 2 | -4 |
| **Total, changing classes** |  | **28** | **34** | **+6** |

The same rows yield `sum Delta n log(rho) = -13.856805065574`, exactly `J_QPD* - J_count*` within `1e-10`. Classes with zero delta account for the remaining eight crossings in each plan. The artifact independently recomputes both objectives from crossed gate occurrences and from aggregated qubit-pair weights for all 36 records.

The sign pattern is the intended heterogeneous-cost mechanism: QPD does not seek fewer crossings unconditionally; it avoids expensive large-angle controlled phases, accepting more low-angle crossings.

QPE exact provides two independent-family reversals. At `n=14`, the QPD optimum accepts one SWAP crossing with `rho=49`, but avoids enough costly controlled phases to reduce `J` by `1.393597` log units. This result is smaller than Draper but confirms the effect is not limited to one family.

## Decision Rule

Predeclared rule:

```text
E6 FULL RELEVANCE PASS:
  at least two eligible algorithm families
  AND at least three strict reversals total
  AND at least one strict reversal not solely from zero/unit-cost gates
  AND exhaustive objective confirmation
```

Observed:

```text
eligible families: 6
strict reversals: 6
families with strict reversal: 2
zero/unit-cost causes: none; corpus-wide exclusion
objective confirmation: exhaustive for 36/36
```

Decision: **E6_FULL_RELEVANCE_PASS**.

## Artifacts

| File | Purpose |
| --- | --- |
| `scripts/run_phase11_3_real_heterogeneous_audit.py` | Reproducible E6 generator, selective decomposition, QPD screening, exhaustive solver |
| `results/phase11_3_algorithm_heterogeneous_audit.json` | Full 36-record audit, gate histograms, objectives, partitions, tradeoffs |
| `results/phase11_3_algorithm_heterogeneous_manifest.json` | Artifact SHA-256, frozen stack, policy, decision |

Artifact SHA-256:

```text
75b63992b616121b89622d6a1b8e865b2b2c4457b818c6c8aac784de0da1a008
```

Reproduce:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\run_phase11_3_real_heterogeneous_audit.py
```

## Verification

```text
E6 script compile: passed
E6 gate-level accounting tests: 2 passed
Full repository regression: 117 passed in 23.44s
```

## Claim Boundary

Use:

```text
On a predeclared 36-circuit MQT Bench algorithm-derived corpus, preserving
algorithm-semantic numeric two-qubit operations reveals six exact balanced partition reversals
between gate-count and Qiskit independent-QPD objectives across two families.
```

Do not use:

```text
real hardware workloads
hardware-native routing result
prevalence across arbitrary algorithms
intrinsic abstract-algorithm shot cost
joint-QPD optimality
```

`ponytail:` E6 fixes equal balanced bipartitions and independent QPD. Add unequal fragments, routing, finite-shot variance, or joint-QPD only when each has a separately frozen protocol and executable validation.
