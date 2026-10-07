from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)
CANONICAL = ROOT / "results" / "e12_representation_placement_regret.json"


def run(*args: str, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def main() -> None:
    env = os.environ.copy()
    env["E12_OUTPUT"] = str(CANONICAL)
    run(str(PYTHON), "scripts/run_e12_representation_placement_regret.py", env=env)
    run(str(PYTHON), "scripts/generate_e12_summary.py")
    run(str(PYTHON), "-m", "pytest", "-q", "tests/test_release_e12_regression.py", "tests/test_e12_solver_consistency.py", "tests/test_ingestion.py")
    print(f"Canonical E12 result: {CANONICAL}")


if __name__ == "__main__":
    main()
