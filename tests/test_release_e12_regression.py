import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _records(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["records"] if isinstance(payload, dict) else payload


def test_release_e12_population_and_reversals_match_manuscript():
    base = _records(ROOT / "results" / "e12_representation_placement_regret.json")
    tight = _records(ROOT / "results" / "e12_representation_placement_regret_feastol_1e-12.json")
    rows = [row for row in base if row.get("tier") == "exact"] + tight
    valid = [row for row in rows if "delta_a_to_b" in row]

    assert len(valid) == 96
    assert Counter(row["family"] for row in valid) == {
        "qaoa": 12, "qft": 12, "qpeexact": 12, "bv": 12,
        "grover": 12, "vqe_real_amp": 12, "ghz": 12, "dj": 12,
    }

    strict = [
        row for row in valid
        if row.get("strict_reversal_a_to_b") or row.get("strict_reversal_b_to_a")
    ]
    assert len(strict) == 8
    assert Counter(row["family"] for row in strict) == {"qpeexact": 3, "grover": 5}

    grover_n10 = next(
        row for row in valid
        if row["family"] == "grover" and row["n"] == 10 and row["K"] == 2
    )
    assert grover_n10["delta_a_to_b"] == pytest.approx(448.23381377659643)
    assert grover_n10["delta_b_to_a"] == pytest.approx(1494.1127125886424)
    assert grover_n10["unitary_verification"]["unitary_equivalence"] == "by_construction"
