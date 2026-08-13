"""Summarize and visualize the replicated E9 capacitated K-way study."""

from __future__ import annotations

import json
import argparse
from collections import defaultdict
from math import log10
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


FIGURES = ROOT / "paper" / "figures"
SUMMARY = ROOT / "results" / "e9_k_heterogeneous_scaling_replicated_summary.json"

FAMILIES = ("random_matching", "community_matching", "weighted_repeat")
SIZES = (20, 32, 40, 60)
FRAGMENTS = (2, 3, 4, 5)
FAMILY_LABELS = {"random_matching": "Random matching", "community_matching": "Community matching", "weighted_repeat": "Weighted repeat"}
COLORS = {"random_matching": "#b2182b", "community_matching": "#2166ac", "weighted_repeat": "#4d9221"}
MARKERS = {2: "o", 3: "s", 4: "^", 5: "D"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "results" / "e9_k_symmetry_scaling.jsonl")
    args = parser.parse_args()
    records = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line]
    if len(records) != 144:
        raise RuntimeError(f"expected 144 E9 records, found {len(records)}")
    grouped: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
    for record in records:
        grouped[record["family"], record["num_qubits"], record["K"]].append(record)
    if any(len(grouped[family, n, k]) != 3 for family in FAMILIES for n in SIZES for k in FRAGMENTS):
        raise RuntimeError("each E9 family-size-K cell must contain three seeds")

    cells = []
    for family in FAMILIES:
        for n in SIZES:
            for k in FRAGMENTS:
                rows = grouped[family, n, k]
                closed = [row for row in rows if row["status"] == "optimal"]
                open_rows = [row for row in rows if row["status"] != "optimal"]
                cells.append({
                    "family": family, "num_qubits": n, "K": k,
                    "closed": len(closed), "replicates": len(rows),
                    "median_runtime_s": float(np.median([row["runtime_s"] for row in rows])),
                    "median_log_gamma_closed": float(np.median([row["objective_log_cost"] for row in closed])) if closed else None,
                    "median_open_log10_factor": float(np.median([log10(row["factor"]) for row in open_rows])) if open_rows else None,
                })
    total_closed = sum(cell["closed"] for cell in cells)
    summary = {"source": str(args.input), "records": len(records), "total_closed": total_closed, "total_replicates": len(records), "cells": cells}
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _heatmap(cells)
    _pareto(cells)
    print(f"Closed {total_closed}/{len(records)}; wrote {SUMMARY}")


def _heatmap(cells: list[dict]) -> None:
    by_key = {(cell["family"], cell["num_qubits"], cell["K"]): cell for cell in cells}
    figure, axes = plt.subplots(1, 3, figsize=(10.8, 3.15), sharey=True, constrained_layout=True)
    image = None
    for axis, family in zip(axes, FAMILIES, strict=True):
        matrix = np.array([[by_key[family, n, k]["closed"] / 3 for k in FRAGMENTS] for n in SIZES])
        image = axis.imshow(matrix, vmin=0, vmax=1, cmap="YlGnBu", aspect="auto")
        axis.set_title(FAMILY_LABELS[family], fontsize=9)
        axis.set_xticks(range(len(FRAGMENTS)), [str(k) for k in FRAGMENTS])
        axis.set_xlabel("Fragments $K$", fontsize=8)
        axis.set_yticks(range(len(SIZES)), [str(n) for n in SIZES])
        for row, n in enumerate(SIZES):
            for column, k in enumerate(FRAGMENTS):
                cell = by_key[family, n, k]
                color = "white" if matrix[row, column] >= 2 / 3 else "black"
                axis.text(column, row, f"{cell['closed']}/3", ha="center", va="center", color=color, fontsize=8, weight="bold")
    axes[0].set_ylabel("Qubits $n$", fontsize=8)
    bar = figure.colorbar(image, ax=axes, shrink=0.88, pad=0.02)
    bar.set_label("Solver-tolerance closure rate", fontsize=8)
    bar.ax.tick_params(labelsize=7)
    for axis in axes:
        axis.tick_params(labelsize=8)
    figure.savefig(FIGURES / "fig_e9_closure_heatmap.pdf", bbox_inches="tight")
    figure.savefig(FIGURES / "fig_e9_closure_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


def _pareto(cells: list[dict]) -> None:
    figure, axis = plt.subplots(figsize=(5.25, 3.65))
    for family in FAMILIES:
        for k in FRAGMENTS:
            # Restrict to fully closed cells: otherwise a median over only easy
            # seeds would condition the width/overhead view on solver success.
            points = [cell for cell in cells if cell["family"] == family and cell["K"] == k and cell["closed"] == cell["replicates"]]
            if not points:
                continue
            axis.scatter(
                [max(cell["num_qubits"] // k + (cell["num_qubits"] % k > 0), 1) for cell in points],
                [cell["median_log_gamma_closed"] for cell in points],
                color=COLORS[family], marker=MARKERS[k], s=37, alpha=0.88,
                edgecolors="black", linewidths=0.35,
            )
    axis.set_xlabel("Maximum fragment width $Q_{\max}$", fontsize=9)
    axis.set_ylabel("Median closed $\log \Gamma^*$", fontsize=9)
    axis.grid(alpha=0.25, linewidth=0.5)
    axis.tick_params(labelsize=8)
    family_handles = [Line2D([], [], color=COLORS[family], marker="o", linestyle="", markersize=5, label=FAMILY_LABELS[family]) for family in FAMILIES]
    k_handles = [Line2D([], [], color="black", marker=MARKERS[k], markerfacecolor="white", linestyle="", markersize=5, label=f"$K={k}$") for k in FRAGMENTS]
    family_legend = axis.legend(handles=family_handles, title="Family", ncol=3, fontsize=7, title_fontsize=7,
                                frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.24),
                                handletextpad=0.3, columnspacing=0.8)
    axis.add_artist(family_legend)
    axis.legend(handles=k_handles, title="Fragments", ncol=4, fontsize=7, title_fontsize=7,
                frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.43),
                handletextpad=0.3, columnspacing=0.8)
    figure.subplots_adjust(bottom=0.33, left=0.14, right=0.98, top=0.97)
    figure.savefig(FIGURES / "fig_e9_width_overhead_pareto.pdf", bbox_inches="tight")
    figure.savefig(FIGURES / "fig_e9_width_overhead_pareto.png", dpi=300, bbox_inches="tight")
    plt.close(figure)


if __name__ == "__main__":
    main()
