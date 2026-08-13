# Artifact Software Versions

The paper uses Python `3.11.9`, Qiskit `2.5.1`, Qiskit Addon Cutting `0.10.0`, PySCIPOpt `6.2.1`, and SCIP `10.0.2`.

- Canonical SCIP suite citation: Bestuzheva et al., *The SCIP Optimization Suite 8.0*, ACM TOMS 49(2), 2023, doi: `10.1145/3585516`.
- Versioned SCIP 10 documentation: https://www.scipopt.org/doc-10.0.2/html/index.php
- Numerically exact MILP mode documentation: https://www.scipopt.org/doc-10.0.2/html/EXACT.php

The paper reports floating-point solver-tolerance bounds, not SCIP exact-mode certificates. The main CertiCut protocol uses an LP tolerance of `1e-9`; the representation-regret rerun pins SCIP `numerics/feastol=1e-12` and sweeps `tau_opt` over `1e-8`, `1e-9`, and `1e-10`.
