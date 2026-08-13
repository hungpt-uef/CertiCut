"""Analyze Track A K=2 restriction penalty from already completed Qiskit Track B data."""

from __future__ import annotations

import json
from math import exp
from pathlib import Path
import statistics


def main() -> None:
    records = [json.loads(line) for line in Path("results/phase6_4_track_b_records.jsonl").read_text(encoding="utf-8").splitlines()]
    tolerance = 1e-8
    overlap_proven = [record for record in records if record.get("track_a_overlap") and record.get("minimum_reached")]
    invariant_violations = [record for record in overlap_proven if abs(record.get("objective_difference") or 0.0) > tolerance]
    proven_practical = [record for record in records if record.get("minimum_reached")]
    penalties = []
    for record in proven_practical:
        delta = (record["certicut_track_a_optimum_log"] if record.get("track_a_overlap") else _track_a_optimum(record["source_id"], record["representation"])) - record["objective_log_cost"]
        penalties.append({
            "source_id": record["source_id"], "representation": record["representation"],
            "max_backjumps": record["qiskit_max_backjumps"], "num_fragments": record["num_fragments"],
            "track_a_overlap": record["track_a_overlap"], "optimum_track_a_log": record["certicut_track_a_optimum_log"] if record.get("track_a_overlap") else _track_a_optimum(record["source_id"], record["representation"]),
            "optimum_track_b_log": record["objective_log_cost"], "delta_k2_log": delta,
            "factor_k2": exp(delta),
        })
    Path("results/phase6_4_k2_penalty_records.jsonl").write_text("".join(json.dumps(row) + "\n" for row in penalties), encoding="utf-8")
    factors = sorted(row["factor_k2"] for row in penalties)
    summary = {
        "source_records": len(records),
        "qiskit_minimum_reached": len(proven_practical),
        "overlap_proven_records": len(overlap_proven),
        "overlap_proof_invariant_violations": len(invariant_violations),
        "overlap_proof_matches": len(overlap_proven) - len(invariant_violations),
        "proven_nonoverlap_records": sum(not row["track_a_overlap"] for row in penalties),
        "restriction_penalty": {
            "records": len(penalties), "factor_one_count": sum(abs(row["delta_k2_log"]) <= tolerance for row in penalties),
            "median_factor": statistics.median(factors), "p90_factor": factors[int(.9 * (len(factors) - 1))], "max_factor": max(factors),
            "positive_penalty_count": sum(row["delta_k2_log"] > tolerance for row in penalties),
        },
        "by_family": _by_family(penalties, tolerance),
    }
    Path("results/phase6_4_k2_penalty_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _track_a_optimum(source_id: str, representation: str) -> float:
    records = [json.loads(line) for line in Path("results/phase6_5b_native_records.jsonl").read_text(encoding="utf-8").splitlines()]
    for record in records:
        if record["source_id"] == source_id and record["representation"] == representation and record["method"] == "milp":
            return record["result"]["objective_log_cost"]
    raise KeyError(f"missing Track A optimum for {source_id}/{representation}")


def _by_family(penalties, tolerance):
    summary = {}
    for family in sorted({row["source_id"].split("/")[1] for row in penalties}):
        subset = [row for row in penalties if row["source_id"].split("/")[1] == family]
        factors = sorted(row["factor_k2"] for row in subset)
        summary[family] = {
            "records": len(subset), "factor_one_count": sum(abs(row["delta_k2_log"]) <= tolerance for row in subset),
            "positive_penalty_count": sum(row["delta_k2_log"] > tolerance for row in subset),
            "median_factor": statistics.median(factors), "max_factor": max(factors),
        }
    return summary


if __name__ == "__main__":
    main()
