# Numerical artifact versions

Reference release environment:

- Python 3.11.9
- Qiskit 2.5.1
- Qiskit Addon Cutting 0.10.0
- MQT QCEC 3.10.0
- PySCIPOpt 6.2.1
- SCIP 10.0.2

Canonical SCIP suite citation: Bestuzheva et al., *The SCIP Optimization Suite 10.0*, arXiv:2511.18580. Versioned SCIP 10.0.2 documentation: https://www.scipopt.org/doc-10.0.2/html/index.php .

The manuscript reports floating-point solver-tolerance results, not SCIP exact-mode certificates. The representation-regret experiment uses one canonical dataset, `results/e12_representation_placement_regret.json`, with symmetric near-balanced capacities `L_k=floor(n/K)` and `U_k=ceil(n/K)` in both exhaustive and SCIP tiers. Its SCIP stages pin `numerics/feastol=1e-10` and sweep `tau_opt` over `1e-7`, `1e-8`, and `1e-9`.

Broader optimization/scaling experiments retain the solver settings stated in their own result records. The complete Python package resolution is stored in `requirements-lock.txt`, while the source commit, reference platform, test count, and release-critical SHA-256 hashes are stored in `results/final_manifest.json`.
