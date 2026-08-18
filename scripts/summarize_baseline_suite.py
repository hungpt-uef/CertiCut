"""Generate frozen E16 summaries, Table VII rows, and quality-runtime figure."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt

from certicut.evaluation.baseline_metrics import summarize_matched_records

OUT = ROOT / "results" / "upgrade_2026" / "e16_baseline_suite"
PAPER_FIGURES = ROOT / "paper" / "figures"


def _rows(corpus: str) -> list[dict]:
    path = OUT / f"{corpus.lower()}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    records = {corpus: _rows(corpus) for corpus in ("E6", "E9", "E10")}
    summary = {corpus: summarize_matched_records(rows) for corpus, rows in records.items()}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    e9 = summary["E9"]
    lines = [
        "\\begin{tabular}{lrrrrrr}", "\\toprule",
        "Method & Feasible & Optimal/closed & Med. $\\Delta J$ & Med. $\\log_{10}R$ & p90 $\\log_{10}R$ & Med. runtime (s)\\\\",
        "\\midrule",
    ]
    for method, values in e9.items():
        lines.append(
            f"{method} & {values['feasible']}/{values['records']} & {values['optimal_on_closed']}/{values['closed_comparisons']} & "
            f"{values['median_delta_log_cost']:.3g} & {values['median_log10_regret']:.3g} & "
            f"{values['p90_log10_regret']:.3g} & {values['median_runtime_s']:.3g}\\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    (OUT / "table_vii.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    figure, axis = plt.subplots(figsize=(6.0, 3.7))
    for method, values in e9.items():
        axis.scatter(values["median_runtime_s"], values["median_log10_regret"], s=55, label=method)
        axis.annotate(method, (values["median_runtime_s"], values["median_log10_regret"]), xytext=(5, 4), textcoords="offset points", fontsize=8)
    axis.set_xscale("log")
    axis.set_xlabel("median end-to-end runtime (s)")
    axis.set_ylabel("median closed-case $\\log_{10} R$")
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(OUT / "fig_e16_quality_runtime.pdf", bbox_inches="tight")
    figure.savefig(OUT / "fig_e16_quality_runtime.png", dpi=300, bbox_inches="tight")
    PAPER_FIGURES.mkdir(parents=True, exist_ok=True)
    figure.savefig(PAPER_FIGURES / "fig_e16_quality_runtime.pdf", bbox_inches="tight")
    figure.savefig(PAPER_FIGURES / "fig_e16_quality_runtime.png", dpi=300, bbox_inches="tight")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
