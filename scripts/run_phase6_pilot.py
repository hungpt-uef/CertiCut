"""Run the deterministic 100-instance / 400-run Track A pilot matrix."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.benchmark.instance import BenchmarkInstance
from certicut.benchmark.runner import run_track_a


def main() -> None:
    records = []
    for n in (8, 12, 16, 20):
        for family in ("community", "nearest_neighbor", "qaoa_ring", "random", "dense"):
            for seed in range(5):
                instance = BenchmarkInstance(family, n, seed)
                for method in ("h2", "h3", "kahip_strong", "phase2_milp", "certicut_b2s_h2"):
                    records.append(run_track_a(instance, method).as_dict())
    Path("results/phase6_pilot_track_a.jsonl").write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    print(json.dumps({"runs": len(records), "errors": sum(record["status"] == "error" for record in records)}, indent=2))


if __name__ == "__main__":
    main()
