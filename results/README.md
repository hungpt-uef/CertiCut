# Result provenance

## Canonical manuscript evidence

The representation-dependence results in the current manuscript are reconstructed from exactly one canonical row-level dataset:

```text
e12_representation_placement_regret.json
```

Its generated aggregate summary is:

```text
e12_canonical_summary.json
```

`final_manifest.json` records the release source commit and SHA-256 hashes of manuscript-critical files.

## Supporting experiments

Other result files in this directory support appendices on optimization scaling, count-versus-QPD comparisons, finite-shot checks, restricted joint-cost checks, and interval verification. They are not merged into the canonical E12 population or used to change its row counts.

## Superseded data

Historical E12 tolerance files and earlier "final evidence" manifests were removed from the current working tree. They remain recoverable through Git history. See `legacy/README.md`.

The current manuscript must not be reconstructed by combining result files from different historical protocol versions.
## QFT single-solution tie audit

`e12_qft_single_solution_tie_audit.json` reproduces the six apparent QFT representation changes obtained by cross-evaluating one optimizer-returned optimum per representation for `n=12,14,16` and `K=2,3`. The largest naive ratio is about `27740.72`. The canonical set-level E12 results for those same six records all have `Delta=0` and `R=1`; the auxiliary audit therefore documents the degeneracy artifact discussed in the manuscript rather than supplying additional positive reversals. Regenerate it with `scripts/audit_qft_single_solution_ties.py`.

## Exact audits of the central representation claims

`e12_qpe14_exhaustive_audit.json` exhaustively enumerates both `n=14` QPE records (`K=2,3`) under the release capacity policy. It independently reproduces the positive representation changes; for the headline `K=2` case it enumerates all 1,716 balanced bipartitions and obtains `R_native_to_cx = 729` with disjoint argmin sets. Regenerate it with `scripts/audit_qpe14_exact.py`.

`e12_qft_exact_set_audit.json` exhaustively enumerates all six QFT cases at `n=12,14,16` and `K=2,3`. Every case has at least one shared optimum across the two representations and zero set-level regret within `1e-10`. Regenerate it with `scripts/audit_qft_exact_sets.py`. Together with `e12_qft_single_solution_tie_audit.json`, this shows that the six large naive cross-evaluation ratios are optimizer-selection artifacts rather than representation-induced changes.
