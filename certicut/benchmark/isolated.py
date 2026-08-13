"""Fresh-process measurement protocol for final runtime and memory claims."""

from __future__ import annotations

from multiprocessing import Pipe, Process
from time import perf_counter
from typing import Any


def run_isolated(payload: dict[str, Any], *, timeout_s: float) -> dict[str, Any]:
    """Run one worker; process time includes startup/IPC, algorithm time does not."""
    parent, child = Pipe(duplex=False)
    started = perf_counter()
    process = Process(target=_worker, args=(child, payload))
    process.start()
    process.join(timeout_s)
    wall_time = perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join()
        return {"status": "timed_out_no_returned_solution", "algorithm_runtime_s": None, "process_wall_time_s": wall_time, "peak_rss_mb": None, "exit_code": process.exitcode, "includes_children": False}
    if not parent.poll():
        return {"status": "worker_no_result", "algorithm_runtime_s": None, "process_wall_time_s": wall_time, "peak_rss_mb": None, "exit_code": process.exitcode, "includes_children": False}
    result = parent.recv()
    result["process_wall_time_s"] = wall_time
    result["exit_code"] = process.exitcode
    result["includes_children"] = False
    return result


def _worker(connection, payload: dict[str, Any]) -> None:
    import os
    import psutil

    thread_limit = payload.get("thread_limit", 1)
    if not isinstance(thread_limit, int) or thread_limit < 1:
        raise ValueError("thread_limit must be a positive integer")
    # Set before SciPy/NumPy imports in this fresh process for reproducible timings.
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[variable] = str(thread_limit)

    from certicut.benchmark.instance import BenchmarkInstance
    from certicut.circuits.ingestion import ingest_mqt_benchmark
    from certicut.graph.interaction import build_interaction_graph
    from certicut.optimization.bnb import solve_certified_bnb

    started = perf_counter()
    try:
        preprocess_started = perf_counter()
        if payload.get("source") == "mqt":
            circuit, audit = ingest_mqt_benchmark(
                payload["family"], payload["num_qubits"], representation=payload["representation"]
            )
            graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
            qmax = (payload["num_qubits"] + 1) // 2
        else:
            instance = BenchmarkInstance(payload["family"], payload["num_qubits"], payload["seed"])
            graph = build_interaction_graph(instance.circuit())
            qmax = instance.qmax
            audit = None
        preprocessing_time = perf_counter() - preprocess_started
        optimizer_started = perf_counter()
        result = solve_certified_bnb(
            graph, qmax=qmax, exact_num_fragments=True,
            lp_variant="b2s_root", warm_start_variant="h2", time_limit_s=payload["algorithm_time_limit_s"],
        )
        process = psutil.Process(os.getpid())
        memory = process.memory_info()
        peak_bytes = getattr(memory, "peak_wset", memory.rss)
        certificate = result.certificate
        connection.send({
            "status": result.status,
            "preprocessing_time_s": preprocessing_time,
            "optimizer_runtime_s": perf_counter() - optimizer_started,
            "end_to_end_algorithm_time_s": perf_counter() - started,
            "algorithm_runtime_s": perf_counter() - started,
            "peak_rss_mb": peak_bytes / 1_000_000,
            "memory_measurement": "isolated_process_peak_working_set",
            "thread_limit": thread_limit,
            "certificate": certificate.as_dict() if certificate else None,
            "expanded_nodes": result.expanded_nodes,
            "timeline": [event.__dict__ for event in result.timeline],
            "audit": audit.as_dict() if audit else None,
        })
    except Exception as error:
        connection.send({"status": "error", "error": repr(error), "preprocessing_time_s": None, "optimizer_runtime_s": None, "end_to_end_algorithm_time_s": perf_counter() - started, "algorithm_runtime_s": perf_counter() - started, "peak_rss_mb": None})
    finally:
        connection.close()
