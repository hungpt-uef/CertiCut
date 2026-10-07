# Reference execution environment

The release is validated on the reference platform below. Numerical SCIP results are floating-point solver results, so bit-for-bit identity across operating systems is not claimed.

- Windows 11, build reported in `results/final_manifest.json`
- Python 3.11.9
- Qiskit 2.5.1
- Qiskit Addon Cutting 0.10.0
- Qiskit Aer 0.17.2
- SciPy 1.17.1
- PySCIPOpt 6.2.1
- SCIP 10.0.2
- MQT Bench 2.2.2
- MQT QCEC 3.10.0
- KaHIP 3.25
- pytest 8.4.2

`requirements.txt` pins the direct research dependencies. `requirements-lock.txt` records the complete Python environment used for the release. `results/final_manifest.json` records the reference platform, scientific file hashes, test count, and canonical E12 summary.

## Clean installation

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe reproducibility\verify_environment.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Canonical representation-regret experiment

The manuscript's representation-regret table is generated from exactly one file:

```text
results/e12_representation_placement_regret.json
```

Reproduce it with:

```powershell
.\.venv\Scripts\python.exe scripts\reproduce_e12.py
```

The runner uses the same symmetric near-balanced capacity policy in the exhaustive and SCIP tiers:

```text
L_k = floor(n/K)
U_k = ceil(n/K)
```

SCIP representation runs pin `numerics/feastol=1e-10` and check `tau_opt` at `1e-7`, `1e-8`, and `1e-9`. This feasibility tolerance is regression-tested against exhaustive references, including the numerically stiff Grover `n=12,K=2` case and a near-balanced QAOA `n=12,K=3` case. A tighter `1e-12` setting was rejected for the release because it produced an incorrect Stage-1 optimum on that Grover reference; it is retained only as a superseded historical artifact. The generated `results/e12_canonical_summary.json` and `paper/tables/e12_regret_rows.tex` are derived from the canonical JSON rather than maintained by hand.

## Semantic checks

Each paired representation carries a parameter-sensitive source fingerprint. Small pairs use dense `Operator` comparison up to global phase. Medium QAOA/QFT/exact-QPE pairs at `n=12,14,16` use MQT QCEC 3.10.0; the QPE `n=14,K=2` main result is therefore independently equivalence-checked. Other tractable expanded pairs use deterministic random-statevector action checks up to global phase. The deepest cases that are not independently checked are explicitly marked `by_construction` in the result record; this is provenance evidence, not a formal equivalence proof.

## Independent exact audits

The two central qualitative claims have additional exhaustive audit paths separate from the production SCIP rows:

```powershell
.\.venv\Scripts\python.exe scripts\audit_qpe14_exact.py
.\.venv\Scripts\python.exe scripts\audit_qft_exact_sets.py
```

The QPE audit exactly enumerates both `n=14` cases (`K=2,3`). The QFT audit exactly enumerates all six `n=12,14,16`, `K=2,3` cases, including 1,009,008 feasible near-balanced partitions for `n=16,K=3`. These audits are intentionally independent checks of the manuscript's positive QPE and negative QFT conclusions.
