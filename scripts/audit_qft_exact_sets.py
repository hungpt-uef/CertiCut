from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from certicut.circuits.ingestion import ingest_mqt_pair

RUNNER = ROOT / "scripts" / "run_e12_representation_placement_regret.py"
OUT = ROOT / "results" / "e12_qft_exact_set_audit.json"


def _load_runner():
    spec = importlib.util.spec_from_file_location("certicut_e12_runner_for_qft_audit", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load E12 runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    runner = _load_runner()
    rows = []
    for n in (12, 14, 16):
        pair = ingest_mqt_pair("qft", n)
        cx, audit = pair["cx_normalized"]
        native, _ = pair["native_qpd"]
        for k in (2, 3):
            result = runner.exhaustive_representation_regret(
                cx, native, K=k, family="qft", n=n,
                source_fingerprint=audit.source_fingerprint,
            )
            rows.append({
                "n": n,
                "K": k,
                "capacity_policy": "symmetric_near_balanced_v1",
                "feasible_partitions_enumerated": result.partition_count,
                "J_cx_star": result.J_a_star,
                "J_native_star": result.J_b_star,
                "delta_cx_to_native": result.delta_a_to_b,
                "delta_native_to_cx": result.delta_b_to_a,
                "R_cx_to_native": result.R_a_to_b,
                "R_native_to_cx": result.R_b_to_a,
                "argmin_cx_count": result.argmin_a_count,
                "argmin_native_count": result.argmin_b_count,
                "optimum_overlap_count": result.optimum_overlap_count,
            })
    payload = {
        "schema": "certicut-qft-exact-set-audit-v1",
        "purpose": "Independent exhaustive verification that all six medium QFT cases have at least one shared optimum across representations.",
        "records": rows,
        "all_have_shared_optimum": all(row["optimum_overlap_count"] > 0 for row in rows),
        "all_set_level_regrets_zero_within_1e-10": all(
            abs(row["delta_cx_to_native"]) <= 1e-10 and abs(row["delta_native_to_cx"]) <= 1e-10
            for row in rows
        ),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(OUT)
    print(json.dumps({
        "records": len(rows),
        "total_partitions_enumerated": sum(r["feasible_partitions_enumerated"] for r in rows),
        "shared_optimum_all": payload["all_have_shared_optimum"],
    }, indent=2))


if __name__ == "__main__":
    main()
