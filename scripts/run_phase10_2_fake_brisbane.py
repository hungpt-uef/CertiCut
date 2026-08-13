"""Run the 20-configuration Phase 10.2 matrix on a frozen official FakeBrisbane snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import real_amplitudes

from certicut.graph.hypergraph import build_hypergraph
from certicut.hardware.calibration import connected_candidate_subgraph, qpu_spec_from_frozen_snapshot
from certicut.optimization.hypergraph_milp import QPUSpec, solve_max_k_cut_unbalanced


ROOT = Path(__file__).resolve().parents[1]


def qaoa_style_circuit(n: int) -> QuantumCircuit:
    circuit = QuantumCircuit(n)
    for qubit in range(n - 1):
        circuit.rzz(np.pi / 4, qubit, qubit + 1)
    for qubit in range(0, n - 2, 2):
        circuit.rzz(np.pi / 3, qubit, qubit + 2)
    return circuit


def candidate_specs(snapshot_path: Path, *, qpus: int, capacity: int) -> tuple[QPUSpec, ...]:
    base = qpu_spec_from_frozen_snapshot(snapshot_path, capacity=capacity)
    specs = []
    for qpu in range(qpus):
        copy = QPUSpec(
            qpu, capacity, base.coupling_edges, base.gate_error_rates,
            base.readout_error_rates, base.physical_qubits,
        )
        specs.append(connected_candidate_subgraph(copy, candidate_count=capacity, seed_site=qpu))
    return tuple(specs)


def run(snapshot_path: Path) -> list[dict]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot["source"] != "qiskit_ibm_runtime_fake_provider":
        raise ValueError("Phase 10.2 offline matrix requires an official FakeProvider snapshot")
    records: list[dict] = []
    for n in (6, 8, 10, 12, 14):
        circuits = (
            ("qaoa_style", qaoa_style_circuit(n)),
            ("vqe_real_amplitudes", real_amplitudes(n, reps=1)),
        )
        for name, circuit in circuits:
            built_at = perf_counter()
            hypergraph = build_hypergraph(
                circuit, block_strategy="temporal_spatial", depth_window=2, max_block_qubits=3
            )
            build_s = perf_counter() - built_at
            for k in (2, 3):
                capacity = (n + k - 1) // k
                started = perf_counter()
                solution = solve_max_k_cut_unbalanced(
                    hypergraph,
                    num_qpus=k,
                    qpu_specs=candidate_specs(snapshot_path, qpus=k, capacity=capacity),
                    alpha=1.0,
                    beta=0.5,
                    gamma=0.5,
                    delta=0.5,
                    require_nonempty_qpus=True,
                )
                solve_s = perf_counter() - started
                record = {
                    "snapshot_backend": snapshot["backend_name"],
                    "snapshot_source": snapshot["source"],
                    "snapshot_sha256": snapshot["sha256"],
                    "candidate_policy": "BFS connected subgraph; candidate_count=logical capacity; seed_site=qpu_id",
                    "circuit": name,
                    "num_qubits": n,
                    "K_qpus": k,
                    "qpu_capacity": capacity,
                    "hyperedges": len(hypergraph.hyperedges),
                    "higher_arity_hyperedges": sum(len(edge.qubits) >= 3 for edge in hypergraph.hyperedges),
                    "status": solution.status,
                    "hypergraph_build_s": round(build_s, 6),
                    "solver_s": round(solve_s, 6),
                    "fragment_sizes": [len(fragment) for fragment in solution.fragments],
                    "cut_hyperedge_count": len(solution.cut_hyperedge_ids),
                    "objective": round(solution.objective_value, 12),
                    "joint_cut_cost": round(solution.cut_cost, 12),
                    "routing_cost": round(solution.routing_cost, 12),
                    "readout_error_cost": round(solution.readout_error_cost, 12),
                    "gate_error_cost": round(solution.gate_error_cost, 12),
                    "partition": solution.partition,
                    "physical_placements": solution.physical_placements,
                }
                records.append(record)
                print(
                    f"[{name} n={n} K={k}] {solution.status}; "
                    f"arity>=3={record['higher_arity_hyperedges']}; solve={solve_s:.3f}s"
                )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "phase10_2_fake_brisbane_matrix.json")
    args = parser.parse_args()
    snapshot = args.snapshot or next((ROOT / "fixtures").glob("ibm_brisbane_fake_calib_*.json"))
    records = run(snapshot)
    args.out.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
