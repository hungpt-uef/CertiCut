"""Experiment script for Step 1: Hypergraph Construction & Max-K-Cut Unbalanced MILP with Noise & Hardware Integration."""

import json
from time import perf_counter
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import NLocal, RealAmplitudes

from certicut.graph.hypergraph import build_hypergraph
from certicut.optimization.hypergraph_milp import QPUSpec, solve_max_k_cut_unbalanced


def generate_hardware_specs(num_qpus: int = 2, qpu_capacity: int = 16) -> list[QPUSpec]:
    """Generate mock IBM Heavy-Hex style hardware & noise maps for QPU targets."""
    specs = []
    for k in range(num_qpus):
        # Create grid/line coupling edges
        edges = []
        for i in range(qpu_capacity - 1):
            edges.append((i, i + 1))
        # Add cross edges for heavy-hex/grid mock
        for i in range(0, qpu_capacity - 4, 4):
            edges.append((i, i + 4))

        # Gate and readout errors
        gate_errs = {(u, v): float(0.005 + 0.002 * ((u + v + k) % 3)) for u, v in edges}
        readout_errs = {i: float(0.01 + 0.005 * ((i + k) % 4)) for i in range(qpu_capacity)}

        specs.append(
            QPUSpec(
                qpu_id=k,
                capacity=qpu_capacity,
                coupling_edges=tuple(edges),
                gate_error_rates=gate_errs,
                readout_error_rates=readout_errs,
            )
        )
    return specs


def run_step1_experiments():
    print("=== Running Step 1 Experiments: Hypergraph & Max-K-Cut Unbalanced MILP ===")

    circuit_sizes = [8, 12, 16, 20, 24]
    results = []

    for n in circuit_sizes:
        # Build test circuits: QAOA and VQE RealAmplitudes
        qaoa_qc = QuantumCircuit(n)
        for i in range(n - 1):
            qaoa_qc.rzz(np.pi / 4, i, i + 1)
        for i in range(0, n - 2, 2):
            qaoa_qc.rzz(np.pi / 3, i, i + 2)

        vqe_qc = RealAmplitudes(n, reps=2).decompose()

        for c_name, qc in [("QAOA", qaoa_qc), ("VQE", vqe_qc)]:
            start_t = perf_counter()
            hg = build_hypergraph(qc)
            hg_build_time = perf_counter() - start_t

            # Run 2-QPU and 3-QPU Unbalanced Max-K-Cut
            for K in [2, 3]:
                cap_per_qpu = (n // K) + 2
                qpu_specs = generate_hardware_specs(num_qpus=K, qpu_capacity=cap_per_qpu + 4)

                milp_start = perf_counter()
                sol = solve_max_k_cut_unbalanced(
                    hg,
                    num_qpus=K,
                    qpu_capacities=[cap_per_qpu] * K,
                    qpu_specs=qpu_specs,
                    alpha=1.0,
                    beta=0.5,
                    gamma=0.5,
                )
                milp_time = perf_counter() - milp_start

                rec = {
                    "num_qubits": n,
                    "circuit": c_name,
                    "K_qpus": K,
                    "num_hyperedges": len(hg.hyperedges),
                    "hg_build_time_s": round(hg_build_time, 5),
                    "status": sol.status,
                    "milp_time_s": round(milp_time, 5),
                    "partition": sol.partition,
                    "fragment_sizes": [len(f) for f in sol.fragments],
                    "cut_hyperedge_count": len(sol.cut_hyperedge_ids),
                    "objective_value": round(sol.objective_value, 5) if sol.objective_value else None,
                    "cut_cost": round(sol.cut_cost, 5) if sol.cut_cost else None,
                    "swap_cost_estimate": round(sol.swap_cost_estimate, 5) if sol.swap_cost_estimate else None,
                    "error_cost": round(sol.error_cost, 5) if sol.error_cost else None,
                }
                results.append(rec)
                print(f"[{c_name} n={n} K={K}] Status: {sol.status} | Hyperedges: {len(hg.hyperedges)} | Cut Edges: {len(sol.cut_hyperedge_ids)} | Obj: {sol.objective_value:.4f} | Time: {milp_time:.4f}s")

    # Save summary
    out_path = "results/step1_hypergraph_milp_summary.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nSaved Step 1 experiment summary to {out_path}")


if __name__ == "__main__":
    run_step1_experiments()
