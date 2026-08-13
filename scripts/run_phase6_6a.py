"""Run isolated wall-clock and memory pilot on a deterministic hard subset."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.benchmark.isolated import run_isolated


def main() -> None:
    records = []
    for family in ("random", "dense", "weighted_random"):
        for n in (24, 26):
            for seed in range(3):
                for budget in (0.5, 1.0, 5.0):
                    result = run_isolated(
                        {"family": family, "num_qubits": n, "seed": seed, "algorithm_time_limit_s": budget},
                        timeout_s=budget + 20.0,
                    )
                    records.append({"family": family, "num_qubits": n, "seed": seed, "budget_s": budget, **result})
    Path("results/phase6_6a_isolated_records.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    print(json.dumps({"records": len(records), "statuses": {status: sum(record["status"] == status for record in records) for status in sorted({record["status"] for record in records})}}, indent=2))


if __name__ == "__main__":
    main()
