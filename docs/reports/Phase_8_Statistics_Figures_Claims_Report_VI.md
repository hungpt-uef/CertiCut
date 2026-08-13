# CertiCut Phase 8 Statistics, Figures, and Claim Audit Report

Ngày: 11/08/2026

## Trạng thái

PASS. Experimental corpus is frozen, provenance/hashes are saved, statistical summaries and bootstrap confidence intervals are generated from raw results, and paper-ready figures/tables/claims are available.

## Frozen Manifest

`results/final_manifest.json` records:

```text
Python 3.11.9
Windows 10 build 26200
Qiskit 2.5.1
Qiskit Addon Cutting 0.10.0
SciPy 1.17.1
KaHIP 3.25
MQT Bench 2.2.2
Matplotlib 3.11.1
cost model: qiskit_qpd_0.10_independent
solver tolerance: 1e-9
safe deadline semantics
SHA-256 hashes of frozen raw artifacts
```

`git_commit=null` is explicit because this workspace is not a Git repository.

## E1 Bootstrap Statistics

All E1 wall-clock proportions use denominator `420`, including cases where no completed safe certificate was available by that requested time. Bootstrap uses fixed seed `20260811`, 2,000 resamples.

| Time | Cert available | Proven | `F<=1.10x` |
| ---: | ---: | ---: | ---: |
| 0.5s | 66.2% [61.4,70.7] | 58.3% [53.6,63.1] | 58.3% [53.6,63.1] |
| 1s | 78.8% [74.8,82.9] | 69.5% [65.2,73.8] | 69.8% [65.2,74.0] |
| 2s | 88.3% [85.2,91.4] | 81.7% [78.1,85.2] | 81.7% [78.1,85.2] |
| 5s | 91.9% [89.3,94.3] | 86.9% [83.8,90.0] | 87.1% [84.0,90.2] |
| 10s | 99.3% [98.3,100] | 92.4% [89.8,94.8] | 92.4% [89.8,94.8] |
| 30s | 100% | 97.1% | 97.1% |
| 60s | 100% | 99.3% | 99.3% |

Conditional `p90 F` is retained only in `results/phase8_statistics.json` and labelled "among available certificates". It is not used in the main proportion table.

## n=40 Family Tail

| Family | Proven / 10 | Median time | p90 time | Median peak MB |
| --- | ---: | ---: | ---: | ---: |
| community | 10/10 | 0.809s | 1.186s | 131.51 |
| nearest-neighbor | 10/10 | 1.646s | 1.764s | 135.78 |
| QAOA ring | 10/10 | 5.367s | 6.173s | 137.41 |
| noisy-community | 9/10 | 2.419s | 18.188s | 131.73 |
| random | 10/10 | 18.344s | 41.224s | 135.97 |
| dense | 10/10 | 24.070s | 52.669s | 136.79 |
| weighted-random | 8/10 | 37.215s | 60.067s | 138.93 |

The final isolated tail is consistent with Phase 3 profiling: unstructured weighted/random/dense topologies drive the n=40 runtime boundary, whereas community/local structure remains easy.

## Generated Figures

```text
paper/figures/fig_anytime_certificate.pdf
paper/figures/fig_scaling_composition.pdf
paper/figures/fig_native_qaoa_representation.pdf
```

## Generated Tables

```text
paper/tables/table_anytime.md
paper/tables/table_scaling.md
paper/tables/table_n40_family_tail.md
paper/tables/table_ablation.md
paper/tables/table_native_qpd.md
paper/tables/table_operational.md
```

## Claim Audit

`paper/claims.md` maps every candidate claim to evidence, evaluated dataset, scope qualifier, and known limitation. It covers certificate semantics, B2S ablation, gate-dependent QPD costs, native representation sensitivity, and practical-Qmax K=2 scope analysis.

## Explicit Limitations

```text
exact balanced K=2 specialization
independent QPD model, not joint-QPD optimum
Qiskit 0.10 decomposition/model dependency
n=40 hard tail; no large-scale claim
logical all-to-all representation, not hardware-aware
exact reconstruction only; no finite-shot variance study
```

## Files

- `scripts/generate_phase8_artifacts.py`
- `results/final_manifest.json`
- `results/phase8_statistics.json`
- `paper/claims.md`
- `paper/figures/*.pdf`
- `paper/tables/*.md`

## Verification

```text
69 passed in 21.81s
```

## Next

Phase 9: write the paper from frozen artifacts. Do not alter solver or experimental protocols. A bug fix requires a new manifest and rerun of affected experiments.

`ponytail:` no p-value flood. Bootstrap confidence intervals support the main E1 proportions; large controlled ablation effects are reported directly with their fixed denominator and scope.
