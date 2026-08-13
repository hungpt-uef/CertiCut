"""Compare paired CX-normalized and native-QPD representations of one MQT source circuit."""

from __future__ import annotations

import json
from math import exp
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.baselines.graph_heuristics import solve_graph_heuristic
from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def main() -> None:
    audits, rows, comparisons = [], [], []
    for family in ("qaoa", "bv", "vqe_real_amp"):
        for n in (8, 12, 16):
            source_id = f"mqt/{family}/n{n}/seed000"
            paired = ingest_mqt_pair(family, n)
            representation_results = {}
            for representation, (circuit, audit) in paired.items():
                audits.append({"source_id": source_id, **audit.as_dict()})
                graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
                qmax = (n + 1) // 2
                h2 = solve_graph_heuristic(graph, qmax=qmax, variant="h2")
                h3 = solve_graph_heuristic(graph, qmax=qmax, variant="h3")
                exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
                certicut = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant="h2")
                representation_results[representation] = {"audit": audit, "exact": exact}
                for method, result in (("h2", h2), ("h3", h3), ("milp", exact), ("certicut", certicut)):
                    rows.append({"source_id": source_id, "representation": representation, "method": method, "result": result.as_dict()})
            cx = representation_results["cx_normalized"]
            native = representation_results["native_qpd"]
            comparisons.append({
                "source_id": source_id, "family": family, "num_qubits": n,
                "source_fingerprint": cx["audit"].source_fingerprint,
                "cx_fingerprint": cx["audit"].circuit_fingerprint,
                "native_fingerprint": native["audit"].circuit_fingerprint,
                "cx_two_qubit_count": cx["audit"].transpiled_two_qubit_count,
                "native_two_qubit_count": native["audit"].transpiled_two_qubit_count,
                "native_gate_types": native["audit"].two_qubit_gate_types,
                "two_qubit_expansion_ratio": cx["audit"].transpiled_two_qubit_count / max(1, native["audit"].transpiled_two_qubit_count),
                "optimum_log_cx": cx["exact"].objective_log_cost,
                "optimum_log_native": native["exact"].objective_log_cost,
                "overhead_ratio_cx_over_native": exp((cx["exact"].objective_log_cost or 0) - (native["exact"].objective_log_cost or 0)),
                "optimal_cut_count_cx": len(cx["exact"].cut_instruction_indices),
                "optimal_cut_count_native": len(native["exact"].cut_instruction_indices),
            })
    Path("results/phase6_5b_native_audits.jsonl").write_text("".join(json.dumps(row) + "\n" for row in audits), encoding="utf-8")
    Path("results/phase6_5b_native_records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    Path("results/phase6_5b_representation_comparison.json").write_text(json.dumps(comparisons, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_circuits": len(comparisons), "representations": len(audits), "method_runs": len(rows), "all_audits_passed": all(row["audit_passed"] for row in audits)}, indent=2))


if __name__ == "__main__":
    main()
