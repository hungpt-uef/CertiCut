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
spec = importlib.util.spec_from_file_location("certicut_e12_runner", RUNNER)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)

OUT = ROOT / "results" / "e12_qpe14_exhaustive_audit.json"


def _record(k: int) -> dict:
    pair = ingest_mqt_pair("qpeexact", 14)
    circuit_a, audit_a = pair["cx_normalized"]
    circuit_b, _ = pair["native_qpd"]
    result = module.exhaustive_representation_regret(
        circuit_a, circuit_b, K=k, family="qpeexact", n=14,
        source_fingerprint=audit_a.source_fingerprint,
    )
    return {
        "n": 14,
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
        "margin_cx": result.margin_a,
        "margin_native": result.margin_b,
    }


def main() -> None:
    records = [_record(2), _record(3)]
    payload = {
        "schema": "certicut-qpe14-exhaustive-audit-v1",
        "purpose": "Independent exhaustive checks of both n=14 QPE representation-regret records used in the manuscript.",
        "records": records,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    old = ROOT / "results" / "e12_qpe14_k2_exhaustive_audit.json"
    if old.exists():
        old.unlink()
    print(OUT)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
