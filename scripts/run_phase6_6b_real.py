"""Resumable isolated E2/E3 real circuit final corpus runner."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.benchmark.isolated import run_isolated


def _run(experiment: str, families: tuple[str, ...], representation: str, output_name: str) -> None:
    output = Path(f"results/{output_name}")
    completed = set()
    if output.exists():
        completed = {(row["family"], row["num_qubits"]) for row in (json.loads(line) for line in output.read_text(encoding="utf-8").splitlines())}
    with output.open("a", encoding="utf-8") as stream:
        for family in families:
            for n in (8, 12, 16, 20, 24):
                if (family, n) in completed:
                    continue
                result = run_isolated({"source": "mqt", "family": family, "num_qubits": n, "seed": 0, "representation": representation, "algorithm_time_limit_s": 60.0}, timeout_s=90.0)
                stream.write(json.dumps({"experiment": experiment, "family": family, "num_qubits": n, "representation": representation, "requested_deadline_s": 60.0, **result}) + "\n")
                stream.flush()


def main() -> None:
    _run("E2_real_cx_normalized", ("qft", "qaoa", "ghz", "bv", "vqe_real_amp"), "cx_normalized", "phase6_6b_e2_real_cx.jsonl")
    _run("E3_real_native_qpd", ("qaoa", "bv", "vqe_real_amp"), "native_qpd", "phase6_6b_e3_native_qpd.jsonl")
    for name in ("phase6_6b_e2_real_cx.jsonl", "phase6_6b_e3_native_qpd.jsonl"):
        rows = [json.loads(line) for line in Path(f"results/{name}").read_text(encoding="utf-8").splitlines()]
        print(json.dumps({"file": name, "records": len(rows), "statuses": {status: sum(row["status"] == status for row in rows) for status in sorted({row["status"] for row in rows})}}, indent=2))


if __name__ == "__main__":
    main()
