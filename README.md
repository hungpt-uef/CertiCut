# CertiCut

**CertiCut** is a research prototype and optimization framework for sampling-aware quantum circuit cutting. It optimizes quasiprobability decomposition (QPD) sampling overhead via log-domain polyhedral relaxations, Branch-and-Bound, and MILP formulations.

---

## Key Features

- **Exact & Relaxed Optimization**:
  - Exact MILP formulations for $K$-way balanced circuit partitioning under independent QPD gate costs.
  - Polyhedral strengthening using B2S (Balanced Cut Cardinality & Triangle Inequalities) for root LP relaxations.
  - Best-Bound Branch-and-Bound solver returning solver-tolerance anytime certificates ($\text{LB} \le \text{OPT} \le \text{UB}$).
  - Benchmark SCIP MIP integration for fast baseline solving and heterogeneous-QPD scaling checks.

- **Sampling-Aware & Gate-Dependent Objectives**:
  - Converts gate-level QPD sampling overhead factors ($\rho_g$) into log-domain edge weights ($w_{ij} = \log \rho_g$) on an interaction graph.
  - Native representation sensitivity analysis (evaluating gate representations like CX, CS, iSWAP, RZZ).
  - Parallel & Joint QPD cost models and operational shot reconstruction pipelines.

- **Reproducible Benchmarking & Auditing**:
  - Fully automated synthetic generator (CNOT-only, varying topologies, $n=16 \dots 60$, $K=2 \dots 5$).
  - MQT Bench real circuit ingestion and Qiskit Addon Cutting (0.10.0) integration.
  - Comprehensive unit test suite (`pytest`) covering core algorithms, relaxations, and SCIP integration.

---

## System Requirements

- **Python**: `3.11.9`
- **SCIP / PySCIPOpt**: SCIP `10.0.2` & `PySCIPOpt 6.2.1`
- **Qiskit Stack**: `qiskit 2.5.1`, `qiskit-addon-cutting 0.10.0`
- **Operating System**: Windows / Linux / macOS

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/hungpt-uef/CertiCut.git
   cd CertiCut
   ```

2. **Set Up Python Environment**:
   It is recommended to use Python 3.11:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   Ensure SCIP (10.0.2) is installed on your system system-wide or via conda/wheels, then install PySCIPOpt and remaining packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## Project Structure

```
CertiCut/
├── certicut/                 # Core Python package
│   ├── benchmark/            # Benchmark schemas, isolated runners, checkpoints
│   ├── circuits/             # Circuit ingestion, MQT bench loaders, synthetics
│   ├── costs/                # QPD gate-cost calculations (independent, joint, parallel)
│   ├── graph/                # Hypergraph, interaction graph, feature extraction
│   ├── hardware/             # Hardware calibration and backend evaluation
│   ├── optimization/         # SCIP core, B2S Branch-and-Bound, LP relaxations, B&B certificates
│   └── qiskit_bridge/        # Operational shot reconstruction and Qiskit Addon Cutting bridge
├── docs/                     # Detailed research reports for all project phases
├── paper/                    # IEEE paper source files, figures, tables, claims audit
├── results/                  # Execution outputs, summary reports, JSON metrics
├── scripts/                  # Experiment runners and evaluation scripts
├── tests/                    # Complete pytest suite (50+ unit tests)
└── requirements.txt          # Package dependencies
```

---

## Usage

### 1. Running Unit Tests

Run the full test suite to verify solver integration, LP strengthening, and QPD cost oracles:
```bash
pytest
```

### 2. Basic Python API Example

Partition a circuit graph into 2 balanced fragments using CertiCut:

```python
from certicut.graph.interaction import InteractionGraph
from certicut.optimization.bnb import solve_certicut_bnb

# Construct interaction graph with log-QPD gate weights
graph = InteractionGraph(num_qubits=8)
# Add CNOT / two-qubit gate interactions
graph.add_edge(0, 1, log_qpd_cost=0.7)
graph.add_edge(1, 2, log_qpd_cost=0.5)

# Solve with CertiCut Branch-and-Bound
result = solve_certicut_bnb(graph, time_limit=10.0)

print(f"Optimal / Best LP Upper Bound: {result.ub}")
print(f"Global Lower Bound: {result.lb}")
print(f"Certified Overhead Factor F <= {result.factor_bound:.4f}")
print(f"Partition Assignment: {result.assignment}")
```

### 3. Running Benchmark Experiments

Execute experiment scripts located in `scripts/`:

- **Run E12 Representation Placement Regret**:
  ```bash
  python scripts/run_e12_representation_placement_regret.py
  ```

- **Summarize E9 $K$-Way Replicated Scaling**:
  ```bash
  python scripts/summarize_e9_k_replicated.py
  ```

---

## Paper & Documentation

- **Paper Source & PDF**: Located in `paper/` (`certicut_ieee.tex`, `certicut_ieee.pdf`).
- **Claims Audit**: Defined in `paper/claims.md`.
- **Phase Reports**: Detailed VI/English technical reports for Phases 0 through 12 are available in `docs/reports/`.
- **Artifact Versions**: Detailed software version audit in `paper/ARTIFACT_VERSIONS.md`.

---

## Citation

If you use CertiCut in your research, please cite:

```bibtex
@article{certicut2026,
  title={CertiCut: Certified Anytime Optimization for Sampling-Aware Quantum Circuit Cutting via Polyhedral Relaxations},
  author={Hung Pung},
  journal={IEEE Transactions on Quantum Engineering},
  year={2026}
}
```
