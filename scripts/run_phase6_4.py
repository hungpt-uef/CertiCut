"""Run Qiskit practical-Qmax Track B gate-only backjump study on paired real circuits."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.baselines.qiskit_cut_finder import qiskit_track_b_record
from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition


def main() -> None:
    records = []
    for family in ("qaoa", "bv", "vqe_real_amp"):
        for n in (8, 12, 16):
            source_id = f"mqt/{family}/n{n}/seed000"
            for representation, (circuit, audit) in ingest_mqt_pair(family, n).items():
                qmax = (n + 1) // 2
                graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
                exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
                # Main effort-controlled study: avoid unbounded Qiskit search on every high-cost representation.
                budgets = (0, 10, 100)
                if n == 8:
                    budgets = (*budgets, None)  # Q-Complete attempt only at the integration-scale rung.
                for backjumps in budgets:
                    try:
                        result = qiskit_track_b_record(
                            circuit, qmax=qmax, seed=0, max_backjumps=backjumps,
                            max_gamma=float("inf"), track_a_optimum_log=exact.objective_log_cost,
                        )
                        records.append({"source_id": source_id, "representation": representation, "cost_model": audit.cost_model, **result})
                    except Exception as error:
                        records.append({"source_id": source_id, "representation": representation, "cost_model": audit.cost_model, "status": "error", "qiskit_max_backjumps": backjumps, "qiskit_max_gamma": "inf", "error": repr(error)})
                    Path("results/phase6_4_track_b_records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    Path("results/phase6_4_track_b_records.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    summary = {
        "records": len(records), "errors": sum(record["status"] == "error" for record in records),
        "minimum_reached": sum(record.get("minimum_reached") is True for record in records),
        "overlap": sum(record.get("track_a_overlap") is True for record in records),
        "fragment_count_distribution": {str(count): sum(record.get("num_fragments") == count for record in records) for count in sorted({record.get("num_fragments") for record in records if record.get("num_fragments") is not None})},
    }
    Path("results/phase6_4_track_b_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
