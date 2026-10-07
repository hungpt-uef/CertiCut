from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qft_single_solution_tie_audit_matches_canonical_set_level_result() -> None:
    audit = json.loads((ROOT / "results/e12_qft_single_solution_tie_audit.json").read_text(encoding="utf-8"))
    assert audit["schema"] == "certicut-qft-tie-audit-v2"
    assert audit["apparent_changes"] == 6
    assert audit["max_single_solution_ratio"] == pytest.approx(27740.721441044498)
    assert audit["max_abs_shared_witness_slack"] <= 1e-10
    for row in audit["records"]:
        assert abs(row["set_level_shared_witness_slack_a"]) <= 1e-10
        assert abs(row["set_level_shared_witness_slack_b"]) <= 1e-10
    canonical = json.loads((ROOT / "results/e12_representation_placement_regret.json").read_text(encoding="utf-8"))
    medium_qft = [r for r in canonical if r["family"] == "qft" and r["tier"] == "scip_set_level"]
    assert len(medium_qft) == 6
    for row in medium_qft:
        assert row["delta_a_to_b"] <= 1e-10
        assert row["delta_b_to_a"] <= 1e-10
        assert row["R_a_to_b"] == pytest.approx(1.0)
        assert row["R_b_to_a"] == pytest.approx(1.0)


import pytest
