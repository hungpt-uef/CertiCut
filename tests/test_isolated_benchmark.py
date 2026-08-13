from certicut.benchmark.isolated import run_isolated


def test_isolated_worker_returns_separate_algorithm_and_process_times() -> None:
    result = run_isolated({"family": "community", "num_qubits": 8, "seed": 0, "algorithm_time_limit_s": 5.0}, timeout_s=15.0)
    assert result["status"] in {"optimal", "time_limit"}
    assert result["algorithm_runtime_s"] is not None
    assert result["process_wall_time_s"] >= result["algorithm_runtime_s"]
    assert result["peak_rss_mb"] is not None
    assert result["includes_children"] is False
