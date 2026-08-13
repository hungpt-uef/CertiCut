# E11 Joint-Aware Model-Regret Gate Report

Ngày: 12/08/2026

## Verdict

**NO-GO cho joint-aware K-way CertiCut v2 làm core, theo evidence hiện có.**

Joint QPD giảm absolute sampling overhead trong theorem class đã kiểm chứng. Tuy nhiên E11 tie-safe không tìm thấy model-induced partition reversal nào trong corpus generated hoặc MQT nhỏ. Một controlled witness có reversal `1.904961607x`; điều này chứng minh hiện tượng tồn tại, không chứng minh prevalence.

Không triển khai arbitrary K-way joint MIP, wire-cut optimizer, hardware-aware core, Benders, branch-and-price, dynamic-cut engine trong vòng này. Chúng sẽ không trả lời được gate quyết định khi semantics joint-QPD hiện chứng minh chỉ cho fixed-bipartition K=2 parallel layers.

## Implemented

- `certicut/optimization/pj_regret.py`
  - exhaustive exact-balanced K=2 evaluator;
  - global label symmetry quotient: qubit `0` fixed to fragment `0`;
  - tie-safe regret:

```text
R_decision =
  min_{P in argmin I} Gamma_J(P)
  / min_P Gamma_J(P)
```

  - reports independent/joint tie counts plus minimum assignment disagreement.
- `scripts/run_e11_exact_model_regret.py`
  - controlled known reversal witness;
  - 60 deterministic synthetic matched-layer circuits;
  - paired MQT representations where ingestion succeeds.
- `tests/test_pj_regret.py`
  - independent tie safety;
  - frozen known-reversal check.

Joint semantics remain restricted:

```text
K = 2
exact balance
common circuit layer
pairwise-disjoint numeric two-qubit gates
parallel Schmitt--Piveteau--Sutter policy
```

The evaluator does not claim general joint QPD, temporal grouping, K-way group semantics, wire cuts, executable hardware decomposition, or formal rational MILP proof.

## E11 Results

| Corpus | Valid | Strict reversal | Max R_decision |
| --- | ---: | ---: | ---: |
| Controlled frozen witness | 1 | 1 | 1.904961607 |
| Synthetic `n={8,10,12}`, depth `{3,5}`, 2 families, 5 seeds | 60 | 0 | 1.0 |
| MQT paired `qaoa,qft,draper_qft_adder`, attempted `n={8,10}` | 8 | 0 | 1.0 |
| Total | 69 | 1 | 1.904961607 |

Two MQT records were ingestion failures, retained in `results/e11_exact_model_regret.json`; no valid record is silently excluded.

The controlled witness is the pre-existing deterministic Phase 10.5 circuit. Its exact tie-safe result is:

```text
independent optimum log cost:              9.980865173557474
joint optimum log cost:                    9.336403318804477
joint cost at best independent optimum:    9.980865173557474
Delta J_decision:                          0.644461854752997
R_decision:                                1.9049616073489846
```

This is structurally relevant: the independent optimum cuts three gates in separate layers; the joint optimum accepts five crossings, including a three-gate parallel layer. Its independent cost is worse, while joint cost is lower. It establishes a non-tie artifact under the implemented policy.

The generated corpus result is negative. Within its topology, gate palette, seeds, exact-balance constraint, and supported PJ policy, independent per-gate cost is an exact placement surrogate. No scientific claim of general equivalence follows.

## Existing Prevalence Rerun

Reran `scripts/run_phase10_6a_prevalence.py`:

| Corpus | Records | Arbitrary-choice reversals | Max reported factor | Mean PJ MILP wall time |
| --- | ---: | ---: | ---: | ---: |
| Synthetic `n={8,10,12}`, 2 families, depth `{3,5}`, 5 seeds | 60 | 2 | 1.537514777 | 0.238 s |

This script chooses one independent optimum lexicographically. It is **not tie-safe**. Therefore its `2/60` is diagnostic only, not prevalence evidence. E11 supersedes it for model-regret claims.

## Representation Factorial

The requested `representation x QPD` factorial cannot be interpreted as a clean source-level effect with current exact PJ semantics:

- Native and CX-normalized circuits differ in gate sequence and parallel-layer structure.
- A representation can create or eliminate legal joint groups.
- Existing MQT pair ingestion supplies `native_qpd` and `cx_normalized`, no separate stable `target-basis` arm.
- All 8 valid paired MQT records had `R_decision=1` under the narrow policy.

Thus current evidence supports only: no detected independent-placement regret in this small paired sample. It cannot rank representation regret against joint-model regret. Add a fixed source manifest, three frozen transpilation policies, supported-gate audit, and larger exact corpus before making RQ2 claims.

## Certificate / Scalability Rerun

Operational joint reconstruction rerun: 8 legal blocks reconstructed Pauli-product expectations below `1e-10` maximum error. Examples:

| Block | Independent Gamma | Joint Gamma |
| --- | ---: | ---: |
| Two parallel CX | 81 | 49 |
| CX + `RZZ(pi/4)` | 52.456 | 33.970563 |
| Two parallel iSWAP | 2,401 | 961 |

Reran `scripts/run_phase10_6c_generic_pilot.py`. Current custom PJ BnB cannot claim useful scalable anytime certificates:

| Instance | Budget | PJ BnB F | Generic pattern MILP |
| --- | ---: | ---: | --- |
| `n=8,d=3` random matching | 0.2 s | 1 | optimal |
| `n=8,d=5` random matching | 0.2 s | `5.49e5` | optimal |
| `n=10,d=3` random matching | 1.0 s | `9.68e4` | optimal |
| `n=10,d=5` ring-even-odd | 1.0 s | `21.12` | optimal |

Generic HiGHS pattern MILP closed all four pilot instances by 1 s. Custom BnB lower bounds remain weak. This directly supports the proposed diagnostic: warm starts/primal search alone are not a certificate-scalability result. No dynamic separation implementation was added because the joint core fails E11's prevalence gate.

## Validation

```text
135 passed in 23.16s
```

Focused joint tests:

```text
24 passed in 2.27s
```

## Artifacts

```text
results/e11_exact_model_regret.json
results/phase10_6a_pj_prevalence.json
results/phase10_4c_operational_joint_reconstruction.json
results/phase10_6c_generic_pilot.json
certicut/optimization/pj_regret.py
scripts/run_e11_exact_model_regret.py
tests/test_pj_regret.py
```

Reproduce:

```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe scripts\run_e11_exact_model_regret.py
.\.venv\Scripts\python.exe scripts\run_phase10_6a_prevalence.py
.\.venv\Scripts\python.exe scripts\run_phase10_4c_operational_study.py
.\.venv\Scripts\python.exe scripts\run_phase10_6c_generic_pilot.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Decision

1. Retain `CertiCut-J` as restricted K=2 parallel joint-QPD theorem and operational-reconstruction result.
2. Do not promote `Joint-aware K-way CertiCut` to v2 core from this evidence.
3. Pivot immediate effort to representation-aware independent-QPD study, or run a substantially broader exact search designed to maximize parallel-group trade-offs before reopening the joint-MIP path.
4. Do not report `n>=100` joint certified scalability. Current joint certificate pilot is open at `n=10` under 1 s.

`ponytail:` general K-way joint groups require a theorem/cost oracle indexed by multi-fragment cut semantics. Add joint K-way MILP only after that oracle and a tie-safe prevalence result exceed the predefined `R_decision > 1.1` gate on a meaningful corpus.
