"""Ingest audited real MQT circuits and run Track A real-circuit sanity matrix."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.baselines.graph_heuristics import solve_graph_heuristic
from certicut.baselines.kahip import solve_kahip
from certicut.circuits.ingestion import ingest_mqt_benchmark
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition


def main() -> None:
    audits, records = [], []
    for family in ("qft", "qaoa", "ghz", "grover", "bv", "vqe_real_amp"):
        for n in (8, 12, 16):
            instance_id = f"mqt/{family}/n{n}/seed000"
            try:
                circuit, audit = ingest_mqt_benchmark(family, n)
                audits.append({"instance_id": instance_id, **audit.as_dict()})
                graph = build_interaction_graph(circuit)
                qmax = (n + 1) // 2
                for name, result in (("h2", solve_graph_heuristic(graph, qmax=qmax, variant="h2")), ("h3", solve_graph_heuristic(graph, qmax=qmax, variant="h3")), ("kahip_fast", solve_kahip(graph, seed=0, mode="fast"))):
                    records.append({"instance_id": instance_id, "method": name, **result.as_dict()})
                exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
                certicut = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2s_root", warm_start_variant="h2")
                records.append({"instance_id": instance_id, "method": "phase2_milp", **exact.as_dict()})
                records.append({"instance_id": instance_id, "method": "certicut_b2s_h2", **certicut.as_dict()})
            except Exception as error:
                audits.append({"instance_id": instance_id, "family": family, "num_qubits": n, "audit_passed": False, "error": repr(error)})
    Path("results/phase6_3_real_audits.jsonl").write_text("".join(json.dumps(row) + "\n" for row in audits), encoding="utf-8")
    Path("results/phase6_3_real_records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
    print(json.dumps({"audits": len(audits), "passed": sum(row.get("audit_passed", False) for row in audits), "method_records": len(records)}, indent=2))


if __name__ == "__main__":
    main()
