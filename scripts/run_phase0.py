"""Run deterministic Phase 0 validation and save raw results."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from certicut.circuits.phase0 import phase0_summary


def main() -> None:
    summary = phase0_summary()
    output = Path("results/phase0_summary.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
