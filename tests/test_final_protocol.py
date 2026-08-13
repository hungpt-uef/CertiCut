from certicut.benchmark.isolated import run_isolated


def test_isolated_record_exposes_preprocessing_optimizer_and_end_to_end_times() -> None:
    result = run_isolated({"family": "community", "num_qubits": 8, "seed": 0, "algorithm_time_limit_s": 5.0}, timeout_s=15.0)
    assert result["status"] in {"optimal", "time_limit"}
    assert result["preprocessing_time_s"] is not None
    assert result["optimizer_runtime_s"] is not None
    assert result["end_to_end_algorithm_time_s"] >= result["preprocessing_time_s"] + result["optimizer_runtime_s"] - 1e-6
    assert result["thread_limit"] == 1
