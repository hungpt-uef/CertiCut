#!/usr/bin/env python3
"""Generate Draper QFT-adder n=16 count-vs-QPD cut topology figure for the paper."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

plt.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42})

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_phase11_3_real_heterogeneous_audit import (  # noqa: E402
    FACTORIES,
    aggregate_pair_weights,
    expose_semantic_two_qubit_ops,
    extract_qpd_gate_records,
)

OUT_PDF = ROOT / "paper" / "figures" / "fig_draper_n16_topology.pdf"
OUT_PNG = ROOT / "paper" / "figures" / "fig_draper_n16_topology.png"
AUDIT = ROOT / "results" / "phase11_3_algorithm_heterogeneous_audit.json"


def _load_frozen_partitions() -> tuple[list[int], list[int]]:
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    for rec in data["records"]:
        if rec["family"] == "draper_qft_adder" and rec["n"] == 16:
            return list(rec["count_optimal_partition"]), list(rec["qpd_optimal_partition"])
    raise RuntimeError("Frozen Draper n=16 record not found")


def _edge_style(log_rho: float) -> tuple[float, str]:
    """Map log overhead to line width and grayscale emphasis."""
    if log_rho >= math.log(5.0):  # roughly CP(pi/2) and above
        return 2.6, "#1a1a1a"
    if log_rho >= math.log(2.0):
        return 1.6, "#555555"
    return 0.8, "#999999"


def _draw_panel(ax, labels: list[int], pair_weights, title: str, subtitle: str) -> None:
    n = len(labels)
    radius = 1.0
    coords = {
        i: (
            radius * math.cos(2 * math.pi * i / n - math.pi / 2),
            radius * math.sin(2 * math.pi * i / n - math.pi / 2),
        )
        for i in range(n)
    }

    # Uncut background edges (light)
    bg_segs = []
    cut_segs = []
    cut_widths = []
    cut_colors = []
    for u, v, _c, w in pair_weights:
        x0, y0 = coords[u]
        x1, y1 = coords[v]
        if labels[u] == labels[v]:
            bg_segs.append([(x0, y0), (x1, y1)])
        else:
            width, color = _edge_style(w)
            cut_segs.append([(x0, y0), (x1, y1)])
            cut_widths.append(width)
            cut_colors.append(color)

    if bg_segs:
        ax.add_collection(
            LineCollection(bg_segs, colors="#d0d0d0", linewidths=0.4, zorder=1, alpha=0.7)
        )
    if cut_segs:
        ax.add_collection(
            LineCollection(cut_segs, colors=cut_colors, linewidths=cut_widths, zorder=2)
        )

    for i, (x, y) in coords.items():
        face = "#2c7bb6" if labels[i] == 0 else "#d7191c"
        ax.add_patch(Circle((x, y), 0.085, facecolor=face, edgecolor="black", linewidth=0.6, zorder=3))
        ax.text(x, y, str(i), ha="center", va="center", fontsize=7, color="white", zorder=4, fontweight="bold")

    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=10, fontweight="bold", pad=6)
    ax.text(0.5, -0.02, subtitle, transform=ax.transAxes, ha="center", va="top", fontsize=8)


def main() -> None:
    count_labels, qpd_labels = _load_frozen_partitions()
    raw = FACTORIES["draper_qft_adder"](16)
    qc = expose_semantic_two_qubit_ops(raw)
    records, unsupported = extract_qpd_gate_records(qc)
    if unsupported:
        raise RuntimeError(f"Unexpected unsupported ops for Draper n=16: {unsupported[:3]}")
    pair_weights = aggregate_pair_weights(records)

    # Verify frozen partitions still evaluate to reported objectives within tolerance.
    from run_phase11_3_real_heterogeneous_audit import evaluate_partition

    c_count, c_j = evaluate_partition(tuple(count_labels), pair_weights)
    q_count, q_j = evaluate_partition(tuple(qpd_labels), pair_weights)
    assert c_count == 36 and abs(c_j - 37.968133) < 1e-4, (c_count, c_j)
    assert q_count == 42 and abs(q_j - 24.111328) < 1e-4, (q_count, q_j)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))
    _draw_panel(
        axes[0],
        count_labels,
        pair_weights,
        "Count-optimal placement",
        rf"$c^*=36$, $J={c_j:.3f}$ ($\Gamma\approx e^{{{c_j:.2f}}}$)",
    )
    _draw_panel(
        axes[1],
        qpd_labels,
        pair_weights,
        "QPD-optimal placement",
        rf"$c=42$, $J={q_j:.3f}$ (factor $1.04\times10^6$)",
    )

    legend = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2c7bb6", markersize=8, label="Fragment 0"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d7191c", markersize=8, label="Fragment 1"),
        Line2D([0], [0], color="#1a1a1a", lw=2.6, label=r"Cut, high $\rho$"),
        Line2D([0], [0], color="#999999", lw=0.8, label=r"Cut, low $\rho$"),
        Line2D([0], [0], color="#d0d0d0", lw=0.8, label="Uncut interaction"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=5, fontsize=7, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("Draper QFT adder ($n=16$): cut topology under count vs. independent-QPD objectives", fontsize=11, y=1.02)
    fig.tight_layout(rect=(0, 0.06, 1, 0.98))
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    print(f"Wrote {OUT_PDF}")
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
