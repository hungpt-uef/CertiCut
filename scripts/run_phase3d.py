"""Profile B0 against B2S-root-pool B&B on Phase 3C hard instances."""

from __future__ import annotations

import json
from math import ceil
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qiskit import QuantumCircuit

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.lp import solve_b2_separated_lp
from scripts.run_phase3c import _stress_circuit


def main() -> None:
    hard = []
    for n in (26, 32, 40):
        for regime_index, regime in enumerate(("random_p10", "random_p50", "community_noise", "weighted_random")):
            for seed in range(2):
                circuit = _stress_circuit(regime, n, 10000 * regime_index + seed)
                graph = build_interaction_graph(circuit)
                qmax = ceil(n / 2)
                root = solve_b2_separated_lp(graph, qmax=qmax, exact_num_fragments=True, policy="top_k", top_k=500)
                if root.relaxation.fractional_variable_count:
                    hard.append((regime, seed, graph, qmax))
    records = []
    for regime, seed, graph, qmax in hard:
        for variant in ("b0", "b2s_root", "b2s_node"):
            result = solve_certified_bnb(
                graph, qmax=qmax, exact_num_fragments=True, node_limit=30, collect_profile=True,
                lp_variant=variant, node_separation_top_k=100, node_separation_max_rounds=3,
                node_separation_depth_limit=1 if variant == "b2s_node" else None,
            )
            assert result.profile is not None and result.certificate is not None
            records.append({
                "regime": regime, "seed": seed, "num_qubits": graph.num_qubits, "variant": variant,
                "status": result.status, "expanded_nodes": result.expanded_nodes,
                "final_log_gap": result.certificate.additive_log_gap,
                **result.profile.__dict__,
            })
    Path("results/phase3d_hard_records.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )
    summary = _summary(records, len(hard))
    Path("results/phase3d_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    Path("results/phase3d_hard_instances.json").write_text(
        json.dumps([{"regime": regime, "seed": seed, "num_qubits": graph.num_qubits} for regime, seed, graph, _ in hard], indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def _summary(records, hard_count):
    def tail(variant, metric):
        values = sorted(float(record[metric]) for record in records if record["variant"] == variant)
        return {"median": statistics.median(values), "p75": values[int(.75 * (len(values) - 1))], "p90": values[int(.9 * (len(values) - 1))], "p95": values[int(.95 * (len(values) - 1))], "max": max(values)}
    return {
        "hard_instance_count": hard_count,
        "b0": {
            "status_counts": _status_counts(records, "b0"),
            "nodes": tail("b0", "expanded_nodes"), "total_time_s": tail("b0", "solve_time_s")
        },
        "b2s_root": {
            "status_counts": _status_counts(records, "b2s_root"),
            "nodes": tail("b2s_root", "expanded_nodes"),
            "total_time_s": tail("b2s_root", "solve_time_s"),
            "root_separation_time_s": tail("b2s_root", "root_separation_time_s"),
            "tree_lp_time_s": tail("b2s_root", "node_lp_time_total_s"),
        },
        "b2s_node": {
            "status_counts": _status_counts(records, "b2s_node"),
            "nodes": tail("b2s_node", "expanded_nodes"),
            "total_time_s": tail("b2s_node", "solve_time_s"),
            "root_separation_time_s": tail("b2s_node", "root_separation_time_s"),
            "tree_lp_time_s": tail("b2s_node", "node_lp_time_total_s"),
            "node_separation_time_s": tail("b2s_node", "node_separation_time_s"),
            "node_cuts": tail("b2s_node", "cuts_discovered_nodes"),
            "stale_reoptimized": tail("b2s_node", "stale_nodes_reoptimized"),
            "reoptimization_bound_gain": tail("b2s_node", "reoptimization_bound_gain_total"),
        },
        "node_reduction": [
            1 - b2s["expanded_nodes"] / b0["expanded_nodes"]
            for b0, b2s in zip(
                [r for r in records if r["variant"] == "b0"],
                [r for r in records if r["variant"] == "b2s_root"],
            ) if b0["expanded_nodes"]
        ],
    }


def _status_counts(records, variant):
    return {
        status: sum(record["variant"] == variant and record["status"] == status for record in records)
        for status in sorted({record["status"] for record in records if record["variant"] == variant})
    }


if __name__ == "__main__":
    main()
