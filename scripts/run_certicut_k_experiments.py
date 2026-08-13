"""Reproducible CertiCut-K matrix plus offline routing/noise diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.hardware.evaluation import controlled_noise_model, evaluate_fragments, evaluate_noisy_z_observable
from certicut.optimization.intervals import log_overhead_interval
from certicut.optimization.k_partition import solve_scip_k_partition


def main() -> None:
    records = []
    for family in ("nearest_neighbor", "community", "random"):
        for qubits, capacities in ((8, ((4, 4), (3, 3, 2))), (10, ((5, 5), (4, 3, 3)))):
            circuit = make_benchmark_circuit(family, qubits, seed=20260812 + qubits)
            graph = build_interaction_graph(circuit)
            for upper in capacities:
                lower = upper
                result = solve_scip_k_partition(
                    graph, num_fragments=len(upper), lower_capacities=lower, upper_capacities=upper, time_limit_s=30.0
                )
                assert result.partition is not None and result.objective_log_cost is not None
                routing = {
                    topology: evaluate_fragments(circuit, result.partition, topology=topology).as_dict()
                    for topology in ("all_to_all", "line", "grid")
                }
                cut_overheads = [gate.qpd_overhead for edge in graph.edges if result.partition[edge.u] != result.partition[edge.v] for gate in edge.gates]
                interval = log_overhead_interval(cut_overheads).as_dict()
                records.append({
                    "family": family,
                    "num_qubits": qubits,
                    "K": len(upper),
                    "capacities": upper,
                    "status": result.status,
                    "partition": result.partition,
                    "fragment_sizes": tuple(map(len, result.fragments)),
                    "log_gamma": result.objective_log_cost,
                    "gamma": result.gamma,
                    "certificate": result.certificate.as_dict() if result.certificate else None,
                    "nodes": result.nodes,
                    "runtime_s": result.runtime_s,
                    "log_interval": interval,
                    "routing": routing,
                })
    # Noise models are built as named controlled scenarios; no QPU calibration claim.
    noise_circuit = make_benchmark_circuit("community", 8, seed=20260812)
    noise = {}
    for name, error in (("low", 0.001), ("medium", 0.005), ("high", 0.01), ("severe", 0.02)):
        model = controlled_noise_model(two_qubit_error=error)
        noise[name] = {
            "two_qubit_error": error,
            "noise_instructions": tuple(model.noise_instructions),
            "all_z_evaluation": evaluate_noisy_z_observable(noise_circuit, model, shots=4096, seed=20260812).as_dict(),
        }
    destination = ROOT / "results" / "certicut_k_experiments.json"
    destination.write_text(json.dumps({"records": records, "controlled_noise_scenarios": noise}, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
