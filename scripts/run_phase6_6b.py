"""Resumable final E1 CertiCut wall-clock corpus runner, isolated per instance."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.benchmark.isolated import run_isolated


FAMILIES = ("community", "nearest_neighbor", "qaoa_ring", "random", "dense", "weighted_random", "noisy_community")
SIZES = (16, 20, 24, 26, 32, 40)
SEEDS = range(10)
DEADLINE_S = 60.0


def main() -> None:
    output = Path("results/phase6_6b_e1_certicut.jsonl")
    completed = set()
    if output.exists():
        completed = {(row["family"], row["num_qubits"], row["seed"]) for row in (json.loads(line) for line in output.read_text(encoding="utf-8").splitlines())}
    with output.open("a", encoding="utf-8") as stream:
        for family in FAMILIES:
            for num_qubits in SIZES:
                for seed in SEEDS:
                    key = (family, num_qubits, seed)
                    if key in completed:
                        continue
                    result = run_isolated(
                        {"family": family, "num_qubits": num_qubits, "seed": seed, "algorithm_time_limit_s": DEADLINE_S, "thread_limit": 1},
                        timeout_s=DEADLINE_S + 30.0,
                    )
                    record = {"experiment": "E1_core_synthetic_track_a_cx", "family": family, "num_qubits": num_qubits, "seed": seed, "requested_deadline_s": DEADLINE_S, "thread_limit": 1, **result}
                    stream.write(json.dumps(record) + "\n")
                    stream.flush()
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    print(json.dumps({"records": len(rows), "target": len(FAMILIES) * len(SIZES) * len(SEEDS), "statuses": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})}}, indent=2))


if __name__ == "__main__":
    main()
