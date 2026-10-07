# CertiCut

Reference implementation and reproducibility materials for **Representation Dependence of Optimal Cut Placement in Quasiprobability Circuit Cutting**.

The study asks whether two semantics-preserving gate-level representations of the same logical circuit can induce different resource-optimal fragment placements under an independent gate-level quasiprobability-decomposition (QPD) cost model.

## Scientific scope

The primary model fixes the logical wire set, fragment count, and capacity family, and changes only the gate-level circuit representation. The independent-QPD objective is optimized as a weighted graph-partitioning problem in log-overhead units. Cross-representation regret is evaluated over optimal-placement sets rather than one arbitrary solver-returned optimum.

The primary model does **not** claim general joint-QPD optimality, wire-cut optimality, routing-aware optimality, hardware-noise optimality, or end-to-end device performance.

## Canonical representation experiment

The manuscript's representation-regret table is generated from one canonical result file:

```text
results/e12_representation_placement_regret.json
```

Every E12 record uses the same symmetric near-balanced capacity policy in both exhaustive and SCIP tiers:

```text
L_k = floor(n/K)
U_k = ceil(n/K)
```

The derived machine-readable summary is:

```text
results/e12_canonical_summary.json
```

and the manuscript table rows are generated from that summary pipeline rather than maintained manually:

```text
paper/tables/e12_regret_rows.tex
```

Reproduce the canonical experiment, summary, and release regression checks with:

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_e12.py
```

## Semantic checks

Paired circuits are generated from the same deterministic MQT Bench source and carry a parameter-sensitive SHA-256 source fingerprint covering instruction order, wire indices, numeric parameters, dimensions, and global phase. Where practical, provenance is supplemented by an independent semantic check:

- small pairs: dense Qiskit `Operator` comparison up to global phase;
- medium QAOA/QFT/exact-QPE pairs at `n=12,14,16`: MQT QCEC 3.10.0 equivalence checking up to global phase;
- other tractable expanded pairs: deterministic random-statevector action checks up to global phase;
- deepest pairs that are not independently simulated: explicitly marked `by_construction` in the result record.

A `by_construction` record is provenance evidence, not a formal equivalence proof. The verification method is stored per result row.

All symbolic MQT source parameters are bound to the same fixed value `pi/4` before either representation is generated; the representation study is therefore a fixed-instance benchmark rather than a parameter sweep.

Independent exhaustive audits additionally reproduce both `n=14` QPE positive cases and all six medium QFT negative cases. See `results/e12_qpe14_exhaustive_audit.json` and `results/e12_qft_exact_set_audit.json`.

## Repository layout

```text
certicut/             Core Python package
scripts/              Public canonical reproduction/generation runners
results/              Canonical and supporting experiment outputs
results/legacy/       Superseded historical artifacts, excluded from manuscript evidence
paper/                LaTeX manuscript, figures, generated tables, references
reproducibility/      Reference environment and environment verifier
tests/                Unit and release-regression tests
requirements.txt      Direct pinned dependencies
requirements-lock.txt Fully resolved Python environment used for the release
```

## Reference environment

The release is validated with Python 3.11.9, Qiskit 2.5.1, Qiskit Addon Cutting 0.10.0, Qiskit Aer 0.17.2, PySCIPOpt 6.2.1, SCIP 10.0.2, MQT Bench 2.2.2, MQT QCEC 3.10.0, and KaHIP 3.25 on the Windows reference platform recorded in `results/final_manifest.json`.

Create and verify a clean environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe reproducibility\verify_environment.py
.\.venv\Scripts\python.exe -m pytest -q
```

See `reproducibility/ENVIRONMENT.md` for numerical-reproducibility semantics and the exact E12 protocol. Floating-point SCIP results are interpreted at the recorded solver tolerances; bit-for-bit equality across operating systems is not claimed.

## Manuscript

```text
paper/certicut.tex
paper/certicut.pdf
```

The manuscript distinguishes exact model-level propositions from floating-point numerical optimization evidence.

## Archived release

Revision-specific Zenodo record: `10.5281/zenodo.23205464` (CertiCut v2.0.0, 2026-10-07).

The stable Zenodo concept DOI for the CertiCut release series is `10.5281/zenodo.21991465`. The earlier record `10.5281/zenodo.22005561` corresponds to v1.0.0 and is retained only as historical provenance.

`results/final_manifest.json` records the source commit, reference environment, canonical E12 summary, validation status, and SHA-256 hashes of release-critical files.

## Citation

See `CITATION.cff` for machine-readable citation metadata.
