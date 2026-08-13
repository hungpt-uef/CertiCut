# CertiCut Phase 11.1 Generic SCIP Audit for Core Independent-QPD Optimization

Ngày: 11/08/2026

## Trạng thái

**AUDIT COMPLETE: NO CUSTOM-SOLVER ADVANTAGE ON THE HARD-90 PILOT.** A mature SCIP backend audit was run for the core independent-QPD, exact-balanced K=2 formulation. The pilot does not support a claim that CertiCut's custom B2S-R plus H2 engine is faster or produces stronger early certificates than generic SCIP on this corpus. SCIP's basic formulation proves all 90 pilot instances with a slightly lower median wall-clock time than CertiCut. Adding static complete-pair cardinality or full B2S triangles to SCIP does not improve the aggregate pilot result and causes time limits on some cases.

This is a positioning result, not a failure of the core sampling-aware formulation or certificate semantics.

## Comparator Setup

All methods optimize the same independent-QPD exact-balanced K=2 objective. The generic models use binary partition labels, XOR crossing variables, fixed label symmetry, and exact balance.

| ID | Backend | Formulation |
| --- | --- | --- |
| G0 | SCIP 10.0.2 / PySCIPOpt 6.2.1 | Basic XOR plus exact balance |
| G1 | SCIP 10.0.2 / PySCIPOpt 6.2.1 | G0 plus complete-pair balanced cut cardinality |
| G2 | SCIP 10.0.2 / PySCIPOpt 6.2.1 | G1 plus all B2S metric triangle facets |
| C | CertiCut | Current B2S-R plus H2 certified B&B |

SCIP reports both primal and dual bounds. CertiCut reports its established safe-boundary certificate. SCIP wall-clock time includes model construction and solving; this corrects an initial instrumentation mistake where SCIP solving time alone excluded model construction.

## Pilot Corpus

```text
90 deterministic CNOT-only synthetic instances
families: community, nearest-neighbor, random, dense, weighted-random, noisy-community
sizes: n = 16, 20, 24
seeds: 0..4
time limit: 2 seconds per method/instance
```

This is an audit pilot aligned with the prior hard-rung family structure. It is not yet the full 420-instance frozen E1 rerun and must not replace published frozen evidence without a new manifest.

## Objective Agreement

All methods that proved the same instance agree on the objective within `1e-8`:

```text
material proven-objective mismatches: 0
```

This validates formulation semantic consistency across G0, G1, G2, and CertiCut for the proven subset.

## Results

| Method | Proven / 90 | Median wall-clock | p90 wall-clock | Median factor |
| --- | ---: | ---: | ---: | ---: |
| G0 SCIP basic | 90 | 0.0640s | 0.1791s | 1.0 |
| G1 SCIP + cardinality | 81 | 0.3373s | 1.3611s | 1.0 among bound-available records |
| G2 SCIP + static B2S | 76 | 0.1020s | 1.5800s | 1.0 among bound-available records |
| C CertiCut B2S-R + H2 | 90 | 0.0692s | 0.4758s | 1.0 |

The hard 2-second outcome is direct:

```text
SCIP basic: 90/90 proven
CertiCut:   90/90 proven
SCIP basic median runtime is slightly lower
```

Static all-pairs cardinality/triangle materialization is not a fair substitute for CertiCut's root separation strategy. Nevertheless, it is a relevant negative result: the present audit does not show a benefit from naively adding the full B2S constraint system to SCIP.

## Interpretation

The supported core contribution is:

```text
sampling-aware independent-QPD cutting objective
exact balanced circuit-cut formulation
circuit-cutting-specific B2S polyhedral reasoning
explicit log-domain certificate semantics
operational independent-QPD reconstruction validation
```

The unsupported claim is:

```text
the current custom CertiCut B&B is faster or universally stronger than mature generic SCIP
```

The audit therefore shifts the safe paper positioning from custom search-engine superiority to a certifiable circuit-cutting formulation and the practical interpretation of global bounds. Future production implementation may use SCIP as a backend while retaining CertiCut's objective, B2S derivation, and certificate interface.

## Limitations

1. The pilot uses a 2-second hard-90 matrix, not the complete E1 checkpoint protocol.
2. G2 adds static triangles, whereas CertiCut uses root separation; this audit does not implement a SCIP separator plugin.
3. No matched 0.1--60 second checkpoint analysis has yet been completed.
4. No SCIP feasible-start injection from H2 was used; SCIP native heuristics remain active and are reported as part of the mature-backend comparison.

## Files

- `certicut/optimization/scip_core.py`
- `tests/test_scip_core.py`
- `scripts/run_phase11_1_scip_pilot.py`
- `results/phase11_1_scip_hard90_pilot.json`

## Decision

Do not market custom B2S-R branch-and-bound as the main algorithmic advantage. Proceed to Phase 11.2 only if the contribution isolation can show why B2S/root separation provides formulation insight beyond a static SCIP model. Before submission, run a complete matched-checkpoint audit or explicitly narrow the performance claim to the frozen CertiCut implementation results without a generic-solver superiority statement.

`ponytail:` permitted wording: “CertiCut provides a circuit-cutting-specific certifiable formulation and an implementation with safe anytime bounds.” Forbidden wording: “CertiCut outperforms mature generic MIP solvers” or “B2S is uniformly beneficial when statically materialized in SCIP.”
