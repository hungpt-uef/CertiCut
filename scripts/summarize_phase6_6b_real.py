"""Summarize isolated E2/E3 final real-circuit records."""

from __future__ import annotations

import json
from pathlib import Path
import statistics


def _summary(path: str):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]
    by_size = {}
    for n in sorted({row["num_qubits"] for row in rows}):
        subset = [row for row in rows if row["num_qubits"] == n]
        by_size[str(n)] = {"records": len(subset), "optimal": sum(row["status"] == "optimal" for row in subset), "median_end_to_end_s": statistics.median(row["end_to_end_algorithm_time_s"] for row in subset), "median_optimizer_s": statistics.median(row["optimizer_runtime_s"] for row in subset), "median_peak_rss_mb": statistics.median(row["peak_rss_mb"] for row in subset)}
    return {"records": len(rows), "statuses": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})}, "by_size": by_size}


def main():
    summary = {"E2": _summary("results/phase6_6b_e2_real_cx.jsonl"), "E3": _summary("results/phase6_6b_e3_native_qpd.jsonl")}
    Path("results/phase6_6b_real_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
