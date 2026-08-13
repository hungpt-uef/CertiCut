"""Phase 10.2 synthetic hardware-aware joint-cutting experiment suite."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import real_amplitudes

from certicut.graph.hypergraph import build_hypergraph
from certicut.optimization.hypergraph_milp import QPUSpec, solve_max_k_cut_unbalanced


ROOT = Path(__file__).resolve().parents[1]


def synthetic_hardware(num_qpus: int, capacity: int) -> tuple[QPUSpec, ...]:
    """Deterministic nonuniform hardware fixtures, not IBM calibration data."""
    specs = []
    for qpu in range(num_qpus):
        sites = tuple(range(capacity))
        edges = tuple((site, site + 1) for site in range(capacity - 1))
        gate_errors = {
            edge: 0.004 + 0.004 * ((edge[0] + edge[1] + qpu) % 3) for edge in edges
        }
        readout_errors = {site: 0.004 + 0.006 * ((site + 2 * qpu) % 4) for site in sites}
        specs.append(QPUSpec(qpu, capacity, edges, gate_errors, readout_errors, sites))
    return tuple(specs)


def qaoa_style_circuit(n: int) -> QuantumCircuit:
    circuit = QuantumCircuit(n)
    for qubit in range(n - 1):
        circuit.rzz(np.pi / 4, qubit, qubit + 1)
    for qubit in range(0, n - 2, 2):
        circuit.rzz(np.pi / 3, qubit, qubit + 2)
    return circuit


def _record(name: str, n: int, k: int, hypergraph, solution, build_s: float, solve_s: float) -> dict:
    return {
        "circuit": name,
        "num_qubits": n,
        "K_qpus": k,
        "hyperedges": len(hypergraph.hyperedges),
        "higher_arity_hyperedges": sum(len(edge.qubits) >= 3 for edge in hypergraph.hyperedges),
        "status": solution.status,
        "hypergraph_build_s": round(build_s, 6),
        "solver_s": round(solve_s, 6),
        "fragment_sizes": [len(fragment) for fragment in solution.fragments],
        "cut_hyperedge_count": len(solution.cut_hyperedge_ids),
        "objective": round(solution.objective_value, 9),
        "joint_cut_cost": round(solution.cut_cost, 9),
        "routing_cost": round(solution.routing_cost, 9),
        "readout_error_cost": round(solution.readout_error_cost, 9),
        "gate_error_cost": round(solution.gate_error_cost, 9),
        "physical_placements": solution.physical_placements,
        "partition": solution.partition,
    }


def run() -> None:
    records = []
    # Exact placement variables scale with logical-pair times physical-site pairs.
    # Keep this acceptance rung small until decomposition is added for larger E7--E9 runs.
    for n in (6, 8):
        circuits = (("qaoa_style", qaoa_style_circuit(n)), ("vqe_real_amplitudes", real_amplitudes(n, reps=1)))
        for name, circuit in circuits:
            started = perf_counter()
            hypergraph = build_hypergraph(
                circuit, block_strategy="temporal_spatial", depth_window=2, max_block_qubits=3
            )
            build_s = perf_counter() - started
            for k in (2, 3):
                capacity = (n + k - 1) // k + 1
                started = perf_counter()
                solution = solve_max_k_cut_unbalanced(
                    hypergraph,
                    num_qpus=k,
                    qpu_specs=synthetic_hardware(k, capacity),
                    alpha=1.0,
                    beta=0.5,
                    gamma=0.5,
                    delta=0.5,
                    require_nonempty_qpus=True,
                )
                solve_s = perf_counter() - started
                record = _record(name, n, k, hypergraph, solution, build_s, solve_s)
                records.append(record)
                print(
                    f"[{name} n={n} K={k}] {solution.status}; "
                    f"hyperedges={record['hyperedges']}, arity>=3={record['higher_arity_hyperedges']}, "
                    f"objective={record['objective']:.5f}, solve={record['solver_s']:.3f}s"
                )
    destination = ROOT / "results" / "phase10_2_hardware_aware_joint_summary.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    run()
