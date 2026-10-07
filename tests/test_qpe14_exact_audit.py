from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_qpe14_exhaustive_audit_confirms_both_n14_witnesses() -> None:
    payload = json.loads((ROOT / "results/e12_qpe14_exhaustive_audit.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "certicut-qpe14-exhaustive-audit-v1"
    rows = {row["K"]: row for row in payload["records"]}
    assert set(rows) == {2, 3}

    k2 = rows[2]
    assert k2["feasible_partitions_enumerated"] == 1716
    assert k2["argmin_cx_count"] == 1
    assert k2["argmin_native_count"] == 1
    assert k2["optimum_overlap_count"] == 0
    assert k2["delta_native_to_cx"] == pytest.approx(6.591673732008616)
    assert k2["R_native_to_cx"] == pytest.approx(729.0)

    k3 = rows[3]
    assert k3["feasible_partitions_enumerated"] == 126126
    assert k3["argmin_cx_count"] == 18
    assert k3["argmin_native_count"] == 1
    assert k3["optimum_overlap_count"] == 0
    assert k3["delta_cx_to_native"] == pytest.approx(3.3134920219647057)
    assert k3["delta_native_to_cx"] == pytest.approx(4.394449154672429)
    assert k3["R_cx_to_native"] == pytest.approx(27.480922096168314)
    assert k3["R_native_to_cx"] == pytest.approx(81.0)

    for row in rows.values():
        assert row["margin_cx"] > 0
        assert row["margin_native"] > 0
