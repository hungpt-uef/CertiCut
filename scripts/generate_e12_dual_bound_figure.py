"""Render representative E12 certificate trajectories from frozen records."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "results" / "upgrade_2026" / "e12_hybrid_certificate" / "dual_bound_profiles" / "records.json"
FIGURES = ROOT / "paper" / "figures"
CELLS = ((40, 3), (40, 4), (40, 5), (60, 5))


def main() -> None:
    records = json.loads(SOURCE.read_text(encoding="utf-8"))
    figure, axes = plt.subplots(2, 2, figsize=(6.8, 4.5), sharex=True)
    for axis, (n, k) in zip(axes.flat, CELLS):
        cell = [record for record in records if record["n"] == n and record["K"] == k]
        for profile, style in (("default", "o-"), ("cardinality_root", "s--")):
            series = sorted((record for record in cell if record["profile"] == profile), key=lambda record: record["budget_s"])
            axis.plot([record["budget_s"] for record in series], [record["log10_F"] for record in series], style, label=profile.replace("_", " "))
        axis.set_title(f"n={n}, K={k}", fontsize=8)
        axis.grid(alpha=0.25)
    for axis in axes[:, 0]:
        axis.set_ylabel(r"$\log_{10}F$")
    for axis in axes[-1, :]:
        axis.set_xlabel("SCIP limit (s)")
    axes[0, 0].legend(fontsize=7)
    figure.tight_layout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    figure.savefig(FIGURES / "fig_e12_dual_bound_profiles.pdf", bbox_inches="tight")
    figure.savefig(FIGURES / "fig_e12_dual_bound_profiles.png", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    main()
