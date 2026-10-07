from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "e12_representation_placement_regret.json"
SUMMARY = ROOT / "results" / "e12_canonical_summary.json"
TABLE = ROOT / "paper" / "tables" / "e12_regret_rows.tex"


def changed(row: dict) -> bool:
    return bool(row.get("strict_reversal_a_to_b") or row.get("strict_reversal_b_to_a"))


def main() -> None:
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise SystemExit("canonical E12 file must be a JSON list")
    if len(rows) != 96:
        raise SystemExit(f"expected 96 canonical E12 records, found {len(rows)}")
    expected = {"qaoa", "qft", "qpeexact", "grover", "bv", "vqe_real_amp", "ghz", "dj"}
    counts = Counter(r["family"] for r in rows)
    if set(counts) != expected or any(counts[k] != 12 for k in expected):
        raise SystemExit(f"unexpected family population: {counts}")
    for row in rows:
        if row.get("protocol_version") != "e12-v3-near-balanced":
            raise SystemExit(f"unexpected E12 protocol version: {row.get('protocol_version')}")
        if row.get("capacity_policy") != "symmetric_near_balanced_v1":
            raise SystemExit(f"missing canonical capacity policy: {row['family']} n={row['n']} K={row['K']}")
        n, k = int(row["n"]), int(row["K"])
        lo, hi = n // k, (n + k - 1) // k
        if row.get("lower_capacities") != [lo] * k or row.get("upper_capacities") != [hi] * k:
            raise SystemExit(f"capacity mismatch: {row['family']} n={n} K={k}")

    changed_rows = [r for r in rows if changed(r)]
    changed_by_family = Counter(r["family"] for r in changed_rows)
    qpe = next(r for r in rows if r["family"] == "qpeexact" and r["n"] == 14 and r["K"] == 2)
    exact_with_kappa = [r for r in rows if r.get("tier") == "exact" and r.get("kappa_a_to_b") is not None]
    kappa_lt_1 = [r for r in exact_with_kappa if r["kappa_a_to_b"] < 1]
    kappa_stable = [r for r in kappa_lt_1 if r["R_a_to_b"] <= 1 + 1e-10]

    summary = {
        "schema": "certicut-e12-summary-v1",
        "canonical_result": str(DATA.relative_to(ROOT)).replace("\\", "/"),
        "capacity_policy": {
            "name": "symmetric_near_balanced_v1",
            "lower": "floor(n/K)",
            "upper": "ceil(n/K)",
        },
        "paired_records": len(rows),
        "records_per_family": dict(sorted(counts.items())),
        "set_level_changes": len(changed_rows),
        "changes_by_family": dict(sorted(changed_by_family.items())),
        "qpe_n14_k2": {
            "delta_cx_to_native": qpe["delta_a_to_b"],
            "delta_native_to_cx": qpe["delta_b_to_a"],
            "R_cx_to_native": qpe["R_a_to_b"],
            "R_native_to_cx": qpe["R_b_to_a"],
            "semantic_check": qpe.get("unitary_verification"),
        },
        "stability_check": {
            "kappa_lt_1": len(kappa_lt_1),
            "kappa_lt_1_and_R1": len(kappa_stable),
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    def stats(families: list[str]):
        subset = [r for r in rows if r["family"] in families]
        changes = sum(changed(r) for r in subset)
        max_ab = max(float(r["delta_a_to_b"]) for r in subset)
        max_ba = max(float(r["delta_b_to_a"]) for r in subset)
        return len(subset), changes, max_ab, max_ba

    specs = [
        ("QAOA", ["qaoa"]),
        ("QFT", ["qft"]),
        ("QPE-exact", ["qpeexact"]),
        ("Grover", ["grover"]),
        ("BV", ["bv"]),
        ("Controls (VQE, GHZ, DJ)", ["vqe_real_amp", "ghz", "dj"]),
    ]
    tex = []
    for label, families in specs:
        n, c, ab, ba = stats(families)
        if label == "Grover":
            left = right = r"Appendix~\ref{app:grover}"
        else:
            left = f"{ab:.2f}" if abs(ab) >= 0.005 else "0.0"
            if label == "QPE-exact":
                right = f"{ba:.2f} ($\\log_{{10}}\\!R\\!=\\!{ba / math.log(10):.2f}$)"
            else:
                right = f"{ba:.2f}" if abs(ba) >= 0.005 else "0.0"
        change_cell = "0" if c == 0 else f"{c} ({100*c/n:.0f}\\%)"
        tex.append(f"{label:<29} & {n} & {change_cell} & {left} & {right}\\\\")
    rows_text = "\n".join(tex) + "\n"
    TABLE.write_text(rows_text, encoding="utf-8")

    manuscript = ROOT / "paper" / "certicut.tex"
    manuscript_text = manuscript.read_text(encoding="utf-8")
    begin = "% BEGIN GENERATED E12 ROWS"
    end = "% END GENERATED E12 ROWS"
    if begin not in manuscript_text or end not in manuscript_text:
        raise SystemExit("manuscript generated-row markers missing")
    before, rest = manuscript_text.split(begin, 1)
    _, after = rest.split(end, 1)
    manuscript.write_text(
        before + begin + "\n" + rows_text + end + after,
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
