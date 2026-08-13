from certicut.benchmark.instance import BenchmarkInstance
from certicut.benchmark.runner import run_track_a


def test_track_a_runner_is_deterministic_and_preserves_certificate_fields() -> None:
    instance = BenchmarkInstance("community", 8, 0)
    first = run_track_a(instance, "certicut_b2s_h2")
    second = run_track_a(instance, "certicut_b2s_h2")
    assert first.instance_id == second.instance_id
    assert first.status == second.status == "optimal"
    assert first.proven_optimal is True
    assert first.log_gap == 0.0
    assert first.objective_log == second.objective_log


def test_track_a_runner_returns_schema_for_heuristic_and_exact_oracle() -> None:
    instance = BenchmarkInstance("random", 8, 1)
    heuristic = run_track_a(instance, "h2")
    exact = run_track_a(instance, "phase2_milp")
    assert heuristic.lb_log is None
    assert heuristic.proven_optimal is None
    assert exact.proven_optimal is True


def test_track_a_runner_records_independent_kahip_baseline() -> None:
    result = run_track_a(BenchmarkInstance("community", 8, 0), "kahip_strong")
    assert result.status == "feasible"
    assert result.lb_log is None
    assert result.proven_optimal is None


def test_hard_rung_families_have_distinct_immutable_ids() -> None:
    weighted = BenchmarkInstance("weighted_random", 24, 0)
    noisy = BenchmarkInstance("noisy_community", 24, 0)
    assert weighted.instance_id != noisy.instance_id
    assert weighted.circuit().size() > 0
    assert noisy.circuit().size() > 0
