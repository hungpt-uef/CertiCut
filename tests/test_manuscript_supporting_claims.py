from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def _json(name: str):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def test_appendix_e5_heterogeneous_count_vs_qpd_statistics() -> None:
    s = _json("phase11_3_heterogeneous_qpd_nonzero_summary.json")
    assert s["records"] == 120
    assert s["status_counts"] == {"optimal": 120}
    assert s["strict_reversals"] == 16
    assert s["strict_reversal_fraction"] == pytest.approx(16 / 120)
    assert s["strict_regret_factor"]["median"] == pytest.approx(5.298825618614838)
    assert s["strict_regret_factor"]["p90"] == pytest.approx(27.466907660465896)
    assert s["strict_regret_factor"]["maximum"] == pytest.approx(181.11466979677732)
    assert s["count_delta"]["median"] == pytest.approx(1.0)
    assert s["count_delta"]["maximum"] == pytest.approx(3.0)
    assert s["gate_delta_totals"]["iswap"] == -28


def test_appendix_e6_algorithm_derived_statistics_and_draper_witness() -> None:
    payload = _json("phase11_3_algorithm_heterogeneous_audit.json")
    rows = [r for r in payload["records"] if r.get("eligible")]
    strict = [r for r in rows if r.get("strict_reversal")]
    assert len(rows) == 36
    assert len(strict) == 6
    assert Counter(r["family"] for r in strict) == {"draper_qft_adder": 4, "qpeexact": 2}
    assert all(not r["strict_reversal"] for r in rows if r["family"] in {"hhl", "qpeinexact", "qft", "qftentangled"})

    d16 = next(r for r in rows if r["family"] == "draper_qft_adder" and r["n"] == 16)
    assert d16["partitions_enumerated"] == 6435
    assert d16["count_optimum"] == 36
    assert d16["min_count_among_qpd_optima"] == 42
    assert d16["J_best_among_count_optima"] == pytest.approx(37.96813325491692)
    assert d16["J_qpd_optimum"] == pytest.approx(24.11132818934327)
    assert d16["regret_factor"] == pytest.approx(1042158.9841052273)
    assert d16["extra_cuts_required"] == 6
    assert sum(x["count_opt_cut"] for x in d16["gate_tradeoff"]) == 36
    assert sum(x["qpd_opt_cut"] for x in d16["gate_tradeoff"]) == 42


def test_appendix_e7_backend_comparison_statistics() -> None:
    s = _json("phase12_e7_heterogeneous_scaling_summary.json")
    assert s["records"] == 200
    expected = {
        "2.0": {"certicut": 160, "g0_basic": 199, "g1_cardinality": 111, "g2_b2s": 108},
        "10.0": {"certicut": 184, "g0_basic": 200, "g1_cardinality": 186, "g2_b2s": 158},
        "60.0": {"certicut": 199, "g0_basic": 200, "g1_cardinality": 196, "g2_b2s": 183},
    }
    for checkpoint, methods in expected.items():
        for method, closed in methods.items():
            assert s["checkpoints"][checkpoint][method]["closed"] == closed


def test_appendix_e9_scaling_and_baseline_statistics() -> None:
    s = _json("e9_k_heterogeneous_scaling_replicated_summary.json")
    assert s["records"] == 144
    assert s["total_closed"] == 101
    cells = {(c["family"], c["num_qubits"], c["K"]): c for c in s["cells"]}
    assert cells[("random_matching", 32, 5)]["median_open_log10_factor"] == pytest.approx(15.466667388334763)
    assert cells[("random_matching", 60, 4)]["median_open_log10_factor"] == pytest.approx(43.47798946002579)

    b = json.loads((RESULTS / "upgrade_2026/e16_baseline_suite/summary.json").read_text(encoding="utf-8"))["E9"]
    expected = {
        "Greedy-Swap": (144, 101, 23, 3.3339416256513292, 1.447912451007929, 10.520662294003081, 0.10004385001957417),
        "Froehler-KL-count": (144, 101, 23, 3.5888022300049656, 1.5585970051332412, 5.007893066301174, 0.10003854997921735),
        "KL-QPD": (144, 101, 68, 3.197442310920451e-14, 1.3886315518367333e-14, 2.938630576651649, 0.10003995010629296),
        "KaHIP-QPD+repair": (144, 101, 51, 3.197442310920451e-13, 1.3886315518367332e-13, 1.4719071411783462, 5.889618200017139),
    }
    for method, (records, closed, matches, med_dj, med_logr, p90_logr, med_t) in expected.items():
        row = b[method]
        assert row["records"] == records
        assert row["feasible"] == records
        assert row["closed_comparisons"] == closed
        assert row["optimal_on_closed"] == matches
        assert row["median_delta_log_cost"] == pytest.approx(med_dj, abs=1e-11)
        assert row["median_log10_regret"] == pytest.approx(med_logr, abs=1e-11)
        assert row["p90_log10_regret"] == pytest.approx(p90_logr)
        assert row["median_runtime_s"] == pytest.approx(med_t)


def test_appendix_e8_finite_shot_scope_statistics() -> None:
    s = _json("phase12_e8_finite_shot_summary.json")
    cases = {r["case_id"]: r for r in s["records"]}
    strong = cases["strong_reversal"]
    moderate = cases["moderate_reversal"]
    control = cases["no_reversal_control"]
    assert strong["witness"]["regret_factor"] == pytest.approx(719.6551181206609)
    assert all(o["paired_rmse_improvement_count_minus_qpd"] > 0 for o in strong["observables"])
    assert moderate["witness"]["regret_factor"] == pytest.approx(3.2671197885950507)
    signs = [o["paired_rmse_improvement_count_minus_qpd"] for o in moderate["observables"]]
    assert signs[0] < 0 < signs[1]
    assert control["witness"]["regret_factor"] == pytest.approx(1.0)
    assert all(o["paired_rmse_improvement_count_minus_qpd"] == pytest.approx(0.0) for o in control["observables"])


def test_appendix_e11_resource_model_witness() -> None:
    rows = _json("e11_exact_model_regret.json")
    r = next(row for row in rows if row.get("family") == "known_reversal_witness")
    assert r["strict_model_reversal"] is True
    assert r["decision_regret_factor"] == pytest.approx(1.9049616073489846)
    assert r["decision_delta_log_cost"] == pytest.approx(0.644461854752997)
    assert r["independent_optimum_count"] == 1
    assert r["parallel_joint_optimum_count"] == 1
