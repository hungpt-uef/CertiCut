# Artifact Software Versions

The paper uses Python `3.11.9`, Qiskit `2.5.1`, Qiskit Addon Cutting `0.10.0`, PySCIPOpt `6.2.1`, and SCIP `10.0.2`.

- Canonical SCIP suite citation: Bestuzheva et al., *The SCIP Optimization Suite 10.0*, arXiv:2511.18580, matching the SCIP `10.0.2` experimental stack.
- Versioned SCIP 10 documentation: https://www.scipopt.org/doc-10.0.2/html/index.php
- Numerically exact MILP mode documentation: https://www.scipopt.org/doc-10.0.2/html/EXACT.php

The paper reports floating-point solver-tolerance bounds, not SCIP exact-mode certificates. Production SCIP runs use the documented feasibility tolerance `numerics/feastol=1e-6`; gap closure is declared externally when `UB-LB<=1e-9`, an external decision threshold rather than a solver tolerance. The reference B2S/HiGHS LP solves use a separately stated `1e-9` LP numerical tolerance; the representation-regret rerun pins SCIP `numerics/feastol=1e-12` and sweeps `tau_opt` over `1e-8`, `1e-9`, and `1e-10`.
