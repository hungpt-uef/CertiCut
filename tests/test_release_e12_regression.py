from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "results" / "e12_representation_placement_regret.json"


def _records() -> list[dict]:
    payload = json.loads(CANONICAL.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    return payload


def _changed(row: dict) -> bool:
    return bool(row.get("strict_reversal_a_to_b") or row.get("strict_reversal_b_to_a"))


def test_release_e12_population_and_reversals_match_manuscript() -> None:
    rows = _records()
    assert len(rows) == 96
    assert Counter(row["family"] for row in rows) == {
        "qaoa": 12,
        "qft": 12,
        "qpeexact": 12,
        "bv": 12,
        "grover": 12,
        "vqe_real_amp": 12,
        "ghz": 12,
        "dj": 12,
    }
    strict = [row for row in rows if _changed(row)]
    assert len(strict) == 8
    assert Counter(row["family"] for row in strict) == {"qpeexact": 3, "grover": 5}


def test_release_e12_uses_one_near_balanced_capacity_policy() -> None:
    for row in _records():
        n, k = int(row["n"]), int(row["K"])
        lo, hi = n // k, (n + k - 1) // k
        assert row["protocol_version"] == "e12-v3-near-balanced"
        assert row["capacity_policy"] == "symmetric_near_balanced_v1"
        assert row["lower_capacities"] == [lo] * k
        assert row["upper_capacities"] == [hi] * k
        if row.get("rep_partition_a") is not None:
            loads = [row["rep_partition_a"].count(i) for i in range(k)]
            assert all(lo <= value <= hi for value in loads)
        if row.get("rep_partition_b") is not None:
            loads = [row["rep_partition_b"].count(i) for i in range(k)]
            assert all(lo <= value <= hi for value in loads)


def test_release_e12_headline_witnesses_and_corrected_grover_case() -> None:
    rows = _records()
    qpe = next(r for r in rows if r["family"] == "qpeexact" and r["n"] == 14 and r["K"] == 2)
    assert qpe["delta_b_to_a"] == pytest.approx(6.591673732008616)
    assert qpe["R_b_to_a"] == pytest.approx(729.0)
    assert qpe["unitary_verification"]["unitary_equivalence"] is True
    assert qpe["unitary_verification"]["method"] == "mqt_qcec"
    assert qpe["unitary_verification"]["equivalence_criterion"] == "equivalent_up_to_global_phase"
    assert qpe["unitary_verification"]["mqt_qcec_version"] == "3.10.0"

    qft = next(r for r in rows if r["family"] == "qft" and r["n"] == 14 and r["K"] == 2)
    assert qft["unitary_verification"]["unitary_equivalence"] is True
    assert qft["unitary_verification"]["method"] == "mqt_qcec"

    grover_n6_k3 = next(r for r in rows if r["family"] == "grover" and r["n"] == 6 and r["K"] == 3)
    assert not _changed(grover_n6_k3)
    assert grover_n6_k3["delta_a_to_b"] == pytest.approx(0.0)
    assert grover_n6_k3["delta_b_to_a"] == pytest.approx(0.0)

    grover_n10 = next(r for r in rows if r["family"] == "grover" and r["n"] == 10 and r["K"] == 2)
    assert grover_n10["delta_a_to_b"] == pytest.approx(448.23381377659643)
    assert grover_n10["delta_b_to_a"] == pytest.approx(1494.1127125886424)
    assert grover_n10["unitary_verification"]["unitary_equivalence"] is True
    assert grover_n10["unitary_verification"]["method"] == "deterministic_random_statevectors_global_phase"


def test_release_e12_scip_rows_pin_numerics_and_tau_sweep() -> None:
    rows = [r for r in _records() if r["tier"] == "scip_set_level"]
    assert len(rows) == 48
    for row in rows:
        assert row["scip_numerics_feastol"] == pytest.approx(1e-10)
        assert row["tau_opt"] == pytest.approx(1e-9)
        assert set(row["tau_sensitivity"]) == {"1e-07", "1e-08", "1e-09"}
        assert row["solver_statuses"] == {
            "stage1_a": "optimal",
            "stage1_b": "optimal",
            "stage2_a_to_b": row["solver_statuses"]["stage2_a_to_b"],
            "stage2_b_to_a": row["solver_statuses"]["stage2_b_to_a"],
        }
        assert row["solver_statuses"]["stage2_a_to_b"] in {"optimal", "trivial", "identical_objectives"}
        assert row["solver_statuses"]["stage2_b_to_a"] in {"optimal", "trivial", "identical_objectives"}
        baseline = (
            row["strict_reversal_a_to_b"],
            row["strict_reversal_b_to_a"],
        )
        for payload in row["tau_sensitivity"].values():
            assert "error" not in payload
            assert (
                payload["strict_reversal_a_to_b"],
                payload["strict_reversal_b_to_a"],
            ) == baseline

def test_release_e12_medium_semantic_verification_is_explicit() -> None:
    rows = _records()
    for family in ("qaoa", "qft", "qpeexact"):
        medium = [
            row for row in rows
            if row["family"] == family and row["tier"] == "scip_set_level"
        ]
        assert len(medium) == 6
        assert {(row["n"], row["K"]) for row in medium} == {
            (12, 2), (12, 3), (14, 2), (14, 3), (16, 2), (16, 3)
        }
        for row in medium:
            verification = row["unitary_verification"]
            assert verification["unitary_equivalence"] is True
            assert verification["method"] == "mqt_qcec"
            assert verification["equivalence_criterion"] in {
                "equivalent", "equivalent_up_to_global_phase"
            }
            assert verification["mqt_qcec_version"] == "3.10.0"

    deep_grover = [
        row for row in rows
        if row["family"] == "grover" and row["tier"] == "scip_set_level"
    ]
    assert len(deep_grover) == 6
    for row in deep_grover:
        verification = row["unitary_verification"]
        assert verification["unitary_equivalence"] == "by_construction"
        assert verification["method"] == "common_parameter_sensitive_source_fingerprint_and_semantics_preserving_expansion"
