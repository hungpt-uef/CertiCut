# CertiCut

Reference implementation and reproducibility materials for **Representation Dependence of Optimal Cut Placement in Quasiprobability Circuit Cutting**.

CertiCut studies a specific question in quasiprobability-based circuit cutting: when two gate-level circuits implement the same logical unitary, can the representation change which fragment placement minimizes the modeled sampling overhead?

The repository contains the optimization model, representation-comparison code, experiment runners, result records, figures, and manuscript source used in the study.

## Main scientific components

- Independent gate-level QPD objective using Qiskit Addon Cutting 0.10.0.
- Capacitated `K`-way weighted graph-partitioning formulation in the log-overhead domain.
- Set-level cross-representation regret that compares complete optimal-placement sets.
- Exhaustive evaluation for small instances and two-stage SCIP evaluation for larger instances.
- Semantic-equivalence checks for paired circuit representations.
- Separate interval-arithmetic verification for a small CX-only tier.

The primary representation result is distinct from backend performance: the central question is whether a semantics-preserving representation change alters the optimal cut-placement set.

## Repository layout

```text
certicut/             Core Python package
scripts/              Selected final experiment/analysis runners
results/              Raw and summarized experiment outputs
paper/                LaTeX manuscript, figures, and references
tests/                Unit and regression tests
requirements.txt      Direct reproducibility dependencies
requirements-lock.txt Fully resolved clean-environment lock
```

## Environment

The manuscript reports the following core versions:

```text
Python                 3.11.9
Qiskit                 2.5.1
Qiskit Addon Cutting   0.10.0
Qiskit Aer             0.17.2
PySCIPOpt              6.2.1
SCIP                    10.0.2
MQT Bench               2.2.2
KaHIP                   3.25
```

Create a fresh environment before reproducing results:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pytest
```

## Manuscript

Current source and compiled PDF:

```text
paper/certicut.tex
paper/certicut.pdf
```

The manuscript distinguishes exact mathematical statements from floating-point optimization results. Public result records are retained in this repository; the archived data release contains the corresponding reproducibility materials, including experiment scripts and solver settings.

## Data release

Archived data and software materials are available on Zenodo:

**DOI:** `10.5281/zenodo.22005561`

## Reproducing experiments

Result files used by the manuscript are stored under `results/`. The final representation-regret runner is included as `scripts/run_e12_representation_placement_regret.py`; the broader experiment suite is distributed with the Zenodo data release. Use `requirements-lock.txt` for the exact resolved Python environment and the software versions, seeds, and solver settings stated by each runner.

## Citation

```bibtex
@article{certicut2026,
  title  = {Representation Dependence of Optimal Cut Placement in Quasiprobability Circuit Cutting},
  author = {Phung Trong Hung and Huong Bui},
  year   = {2026}
}
```

## Scope

The primary optimization model covers gate cuts with independent per-gate QPD costs on a fixed logical wire set and fixed capacity constraints. Wire cutting, hardware routing, hardware noise, and general joint-QPD optimization are outside that primary model.
