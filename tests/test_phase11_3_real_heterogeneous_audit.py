"""Regression checks for E6 exact balanced enumeration."""

import importlib.util
import json
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "phase11_3_real_heterogeneous_audit",
    Path(__file__).parents[1] / "scripts" / "run_phase11_3_real_heterogeneous_audit.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_exact_balanced_enumeration_prefers_qpd_among_count_ties():
    result = MODULE.solve_exact_balanced(
        4,
        [(0, 1, 1, 10.0), (0, 2, 2, 2.0), (0, 3, 2, 2.0)],
    )

    assert result["partitions_enumerated"] == 3
    assert result["count_optimum"] == 3
    assert result["J_best_among_count_optima"] == 12.0
    assert result["J_qpd_optimum"] == 4.0
    assert result["strict_reversal"] is True
    assert result["extra_cuts_required"] == 1


def test_gate_level_accounting_matches_pair_aggregation():
    records = [
        {"q0": 0, "q1": 1, "pair": (0, 1), "gate": {"name": "a", "params": ()}, "rho": 9.0, "log_rho": MODULE.math.log(9.0)},
        {"q0": 0, "q1": 2, "pair": (0, 2), "gate": {"name": "b", "params": ()}, "rho": 3.0, "log_rho": MODULE.math.log(3.0)},
        {"q0": 0, "q1": 3, "pair": (0, 3), "gate": {"name": "b", "params": ()}, "rho": 3.0, "log_rho": MODULE.math.log(3.0)},
    ]
    pair_weights = MODULE.aggregate_pair_weights(records)
    result = MODULE.solve_exact_balanced(4, pair_weights)

    consistency = MODULE.validate_gate_level_objectives(result, records, pair_weights)
    tradeoff = MODULE.gate_tradeoff(result, records)

    assert consistency["count_opt_gate_level_J"] == result["J_best_among_count_optima"]
    assert sum(row["delta_qpd_minus_count"] for row in tradeoff) == result["extra_cuts_required"]
    assert abs(sum(row["delta_log_cost"] for row in tradeoff) - (result["J_qpd_optimum"] - result["J_best_among_count_optima"])) <= MODULE.OBJ_TOL


def test_frozen_e6_artifact_has_complete_gate_level_accounting():
    artifact_path = Path(__file__).parents[1] / "results" / "phase11_3_algorithm_heterogeneous_audit.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["representation_policy"] == "algorithm_semantic_2q_preserving"
    assert artifact["decision"] == "E6_FULL_RELEVANCE_PASS"
    assert len(artifact["records"]) == 36
    assert all(record["eligible"] for record in artifact["records"])

    reversals = [record for record in artifact["records"] if record["strict_reversal"]]
    assert len(reversals) == 6
    for record in artifact["records"]:
        consistency = record["gate_level_consistency"]
        assert abs(consistency["count_opt_gate_level_J"] - record["J_best_among_count_optima"]) <= MODULE.OBJ_TOL
        assert abs(consistency["qpd_opt_gate_level_J"] - record["J_qpd_optimum"]) <= MODULE.OBJ_TOL
    for record in reversals:
        assert sum(row["delta_qpd_minus_count"] for row in record["gate_tradeoff"]) == record["extra_cuts_required"]
        gate_delta = sum(row["delta_log_cost"] for row in record["gate_tradeoff"])
        objective_delta = record["J_qpd_optimum"] - record["J_best_among_count_optima"]
        assert abs(gate_delta - objective_delta) <= MODULE.OBJ_TOL
