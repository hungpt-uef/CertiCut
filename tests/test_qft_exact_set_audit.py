from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qft_exact_set_audit_confirms_all_six_shared_optima() -> None:
    audit = json.loads((ROOT / "results/e12_qft_exact_set_audit.json").read_text(encoding="utf-8"))
    assert audit["schema"] == "certicut-qft-exact-set-audit-v1"
    assert len(audit["records"]) == 6
    assert audit["all_have_shared_optimum"] is True
    assert audit["all_set_level_regrets_zero_within_1e-10"] is True
    expected_counts = {
        (12, 2): 462,
        (12, 3): 5775,
        (14, 2): 1716,
        (14, 3): 126126,
        (16, 2): 6435,
        (16, 3): 1009008,
    }
    for row in audit["records"]:
        key = (row["n"], row["K"])
        assert row["feasible_partitions_enumerated"] == expected_counts[key]
        assert row["optimum_overlap_count"] > 0
        assert abs(row["delta_cx_to_native"]) <= 1e-10
        assert abs(row["delta_native_to_cx"]) <= 1e-10
