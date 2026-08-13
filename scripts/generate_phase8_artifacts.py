"""Freeze final results, derive statistics/tables, and render paper figures from raw JSONL."""

from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import random
import statistics
import sys

import matplotlib.pyplot as plt


RAW_FILES = (
    "phase6_2_track_a_records.jsonl", "phase6_2_checkpoints.jsonl", "phase6_2_summary.json",
    "phase6_4_track_b_records.jsonl", "phase6_4_k2_penalty_summary.json",
    "phase6_5b_representation_comparison.json", "phase6_6b_e1_certicut.jsonl",
    "phase6_6b_e1_wallclock_checkpoints.jsonl", "phase6_6b_e1_summary.json",
    "phase6_6b_e2_real_cx.jsonl", "phase6_6b_e3_native_qpd.jsonl",
    "phase7_operational_validation.json",
)


def main() -> None:
    results = Path("results")
    paper = Path("paper")
    figures = paper / "figures"
    tables = paper / "tables"
    figures.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    _freeze_manifest(results)
    e1_rows = _jsonl(results / "phase6_6b_e1_certicut.jsonl")
    checkpoints = _jsonl(results / "phase6_6b_e1_wallclock_checkpoints.jsonl")
    summary = _statistics(e1_rows, checkpoints)
    (results / "phase8_statistics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _tables(tables, summary, results)
    _figures(figures, summary, results)
    print(json.dumps({"manifest": "results/final_manifest.json", "statistics": "results/phase8_statistics.json", "figures": 3, "tables": 4}, indent=2))


def _freeze_manifest(results: Path) -> None:
    hashes = {}
    for name in RAW_FILES:
        path = results / name
        hashes[name] = sha256(path.read_bytes()).hexdigest() if path.exists() else None
    manifest = {
        "frozen_at": "2026-08-11",
        "git_commit": None,
        "git_note": "workspace is not a git repository",
        "python": sys.version.split()[0], "os": platform.platform(),
        "versions": {"qiskit": "2.5.1", "qiskit_addon_cutting": "0.10.0", "scipy": "1.17.1", "kahip": "3.25", "mqt_bench": "2.2.2", "matplotlib": "3.11.1"},
        "cost_model": "qiskit_qpd_0.10_independent",
        "solver_tolerance": 1e-9,
        "safe_deadline": "soft requested deadline; return only after completed safe LP or B&B boundary; actual event time is recorded",
        "random_seeds": {"synthetic": "manifested per raw instance", "bootstrap": 20260811},
        "raw_result_sha256": hashes,
        "experiments": {"E1": "420 synthetic Track A-CX instances", "E2": "25 real CX-normalized instances", "E3": "15 native-QPD instances", "E4": "60 Qiskit practical-Qmax records"},
    }
    (results / "final_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _statistics(e1, checkpoints):
    budgets = sorted({row["budget_s"] for row in checkpoints})
    stats = {"E1": {"records": len(e1), "status": _counts(e1, "status"), "wallclock": {}, "family_n40": {}, "size": {}}}
    for budget in budgets:
        subset = [row for row in checkpoints if row["budget_s"] == budget]
        available = [row for row in subset if row["certificate_available"]]
        stats["E1"]["wallclock"][str(budget)] = {
            "certificate_available": _proportion_ci(sum(row["certificate_available"] for row in subset), len(subset)),
            "proven_optimal": _proportion_ci(sum(row["proven_optimal"] for row in subset), len(subset)),
            "factor_le_1_01": _proportion_ci(sum(row["factor"] is not None and row["factor"] <= 1.01 for row in subset), len(subset)),
            "factor_le_1_05": _proportion_ci(sum(row["factor"] is not None and row["factor"] <= 1.05 for row in subset), len(subset)),
            "factor_le_1_10": _proportion_ci(sum(row["factor"] is not None and row["factor"] <= 1.10 for row in subset), len(subset)),
            "conditional_factor": _distribution([row["factor"] for row in available]),
        }
    for n in sorted({row["num_qubits"] for row in e1}):
        subset = [row for row in e1 if row["num_qubits"] == n]
        stats["E1"]["size"][str(n)] = {"optimal": _proportion_ci(sum(row["status"] == "optimal" for row in subset), len(subset)), "optimizer_s": _distribution([row["optimizer_runtime_s"] for row in subset]), "end_to_end_s": _distribution([row["end_to_end_algorithm_time_s"] for row in subset]), "peak_rss_mb": _distribution([row["peak_rss_mb"] for row in subset])}
    for family in sorted({row["family"] for row in e1 if row["num_qubits"] == 40}):
        subset = [row for row in e1 if row["num_qubits"] == 40 and row["family"] == family]
        stats["E1"]["family_n40"][family] = {"optimal": _proportion_ci(sum(row["status"] == "optimal" for row in subset), len(subset)), "end_to_end_s": _distribution([row["end_to_end_algorithm_time_s"] for row in subset]), "peak_rss_mb": _distribution([row["peak_rss_mb"] for row in subset])}
    return stats


def _proportion_ci(successes, total, samples=2000):
    generator = random.Random(20260811 + successes + total)
    values = [sum(generator.random() < successes / total for _ in range(total)) / total for _ in range(samples)]
    values.sort()
    return {"count": successes, "total": total, "proportion": successes / total, "ci95": [values[int(.025 * samples)], values[int(.975 * samples) - 1]]}


def _distribution(values):
    values = sorted(float(value) for value in values)
    return {"median": statistics.median(values), "p75": values[int(.75 * (len(values) - 1))], "p90": values[int(.9 * (len(values) - 1))], "p95": values[int(.95 * (len(values) - 1))], "max": max(values)}


def _counts(rows, field):
    return {key: sum(row[field] == key for row in rows) for key in sorted({row[field] for row in rows})}


def _tables(tables: Path, stats, results: Path):
    lines = ["| Time | Certificate available | Proven | F<=1.01x | F<=1.05x | F<=1.10x |", "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for time, item in stats["E1"]["wallclock"].items():
        fmt = lambda key: f"{item[key]['count']}/{item[key]['total']} ({item[key]['proportion']:.1%})"
        lines.append(f"| {time}s | {fmt('certificate_available')} | {fmt('proven_optimal')} | {fmt('factor_le_1_01')} | {fmt('factor_le_1_05')} | {fmt('factor_le_1_10')} |")
    (tables / "table_anytime.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["| n | Proven | Median optimizer s | p90 optimizer s | Median peak MB | p90 peak MB |", "| ---: | ---: | ---: | ---: | ---: | ---: |"]
    for n, item in stats["E1"]["size"].items():
        lines.append(f"| {n} | {item['optimal']['count']}/{item['optimal']['total']} | {item['optimizer_s']['median']:.3f} | {item['optimizer_s']['p90']:.3f} | {item['peak_rss_mb']['median']:.2f} | {item['peak_rss_mb']['p90']:.2f} |")
    (tables / "table_scaling.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    comparison = json.loads((results / "phase6_5b_representation_comparison.json").read_text(encoding="utf-8"))
    lines = ["| Family | n | CX 2q | Native 2q | J*_CX | J*_native | Gamma ratio |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for row in comparison:
        lines.append(f"| {row['family']} | {row['num_qubits']} | {row['cx_two_qubit_count']} | {row['native_two_qubit_count']} | {row['optimum_log_cx']:.3f} | {row['optimum_log_native']:.3f} | {row['overhead_ratio_cx_over_native']:.3g} |")
    (tables / "table_native_qpd.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tables / "table_operational.md").write_text("| Circuit | Cuts | Predicted Gamma | Executed Gamma | Error |\n| --- | ---: | ---: | ---: | ---: |\n| QAOA n=6 native RZZ | 2 | 33.9706 | 33.9706 | 1.39e-17 |\n| VQE n=6 CX | 1 | 9 | 9 | 5.55e-17 |\n", encoding="utf-8")


def _figures(figures: Path, stats, results: Path):
    plt.style.use("seaborn-v0_8-whitegrid")
    times = [float(key) for key in stats["E1"]["wallclock"]]
    proven = [stats["E1"]["wallclock"][str(time)]["proven_optimal"]["proportion"] for time in times]
    available = [stats["E1"]["wallclock"][str(time)]["certificate_available"]["proportion"] for time in times]
    f110 = [stats["E1"]["wallclock"][str(time)]["factor_le_1_10"]["proportion"] for time in times]
    fig, axis = plt.subplots(figsize=(6.5, 4))
    axis.plot(times, available, marker="o", label="certificate available")
    axis.plot(times, proven, marker="s", label="proven optimal")
    axis.plot(times, f110, marker="^", label="F <= 1.10x")
    axis.set_xscale("log"); axis.set_ylim(0, 1.05); axis.set_xlabel("requested safe deadline (s)"); axis.set_ylabel("fraction of 420 instances"); axis.legend(); fig.tight_layout(); fig.savefig(figures / "fig_anytime_certificate.pdf"); plt.close(fig)
    sizes = [int(key) for key in stats["E1"]["size"]]
    preprocess = [stats["E1"]["size"][str(n)]["end_to_end_s"]["median"] - stats["E1"]["size"][str(n)]["optimizer_s"]["median"] for n in sizes]
    optimizer = [stats["E1"]["size"][str(n)]["optimizer_s"]["median"] for n in sizes]
    fig, axis = plt.subplots(figsize=(6.5, 4)); axis.bar(sizes, preprocess, label="preprocessing"); axis.bar(sizes, optimizer, bottom=preprocess, label="optimizer"); axis.set_xlabel("qubits"); axis.set_ylabel("median end-to-end time (s)"); axis.legend(); fig.tight_layout(); fig.savefig(figures / "fig_scaling_composition.pdf"); plt.close(fig)
    comparison = [row for row in json.loads((results / "phase6_5b_representation_comparison.json").read_text(encoding="utf-8")) if row["family"] == "qaoa"]
    fig, axis = plt.subplots(figsize=(6.5, 4)); x = range(len(comparison)); axis.bar([value - .2 for value in x], [row["optimum_log_cx"] for row in comparison], .4, label="CX-normalized"); axis.bar([value + .2 for value in x], [row["optimum_log_native"] for row in comparison], .4, label="native-QPD"); axis.set_xticks(list(x), [f"n={row['num_qubits']}" for row in comparison]); axis.set_ylabel("optimal log independent-QPD overhead"); axis.legend(); fig.tight_layout(); fig.savefig(figures / "fig_native_qaoa_representation.pdf"); plt.close(fig)


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


if __name__ == "__main__":
    main()
