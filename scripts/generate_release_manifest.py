from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "final_manifest.json"

FILES = [
    ".gitignore",
    "README.md",
    "CITATION.cff",
    "requirements.txt",
    "requirements-lock.txt",
    "reproducibility/ENVIRONMENT.md",
    "reproducibility/verify_environment.py",
    "results/README.md",
    "results/legacy/README.md",
    "paper/ARTIFACT_VERSIONS.md",
    "certicut/circuits/ingestion.py",
    "certicut/costs/qpd.py",
    "certicut/graph/interaction.py",
    "certicut/optimization/exact.py",
    "certicut/optimization/k_partition.py",
    "certicut/optimization/pj_regret.py",
    "scripts/run_e12_representation_placement_regret.py",
    "scripts/generate_e12_summary.py",
    "scripts/reproduce_e12.py",
    "scripts/audit_qft_single_solution_ties.py",
    "scripts/audit_qft_exact_sets.py",
    "scripts/audit_qpe14_exact.py",
    "tests/test_ingestion.py",
    "tests/test_release_e12_regression.py",
    "tests/test_e12_solver_consistency.py",
    "tests/test_qft_tie_audit.py",
    "tests/test_qft_exact_set_audit.py",
    "tests/test_qpe14_exact_audit.py",
    "tests/test_qcec_criterion_parsing.py",
    "tests/test_manuscript_qpd_cost_claims.py",
    "tests/test_manuscript_qaoa_scaling_claim.py",
    "tests/test_manuscript_supporting_claims.py",
    "results/e12_representation_placement_regret.json",
    "results/e12_canonical_summary.json",
    "results/e12_qft_single_solution_tie_audit.json",
    "results/e12_qft_exact_set_audit.json",
    "results/e12_qpe14_exhaustive_audit.json",
    "results/phase11_3_heterogeneous_qpd_nonzero_summary.json",
    "results/phase11_3_algorithm_heterogeneous_audit.json",
    "results/phase12_e7_heterogeneous_scaling_summary.json",
    "results/e9_k_heterogeneous_scaling_replicated_summary.json",
    "results/upgrade_2026/e16_baseline_suite/summary.json",
    "results/phase12_e8_finite_shot_summary.json",
    "results/e11_exact_model_regret.json",
    "paper/certicut.tex",
    "paper/references.bib",
    "paper/certicut.pdf",
    "paper/figures/fig_certicut_architecture.tex",
    "paper/figures/fig_certicut_architecture.pdf",
    "paper/tables/e12_regret_rows.tex",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def git_status_porcelain() -> list[str]:
    output = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    return [line for line in output.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pytest-passed", type=int, required=True)
    parser.add_argument("--pdf-pages", type=int, required=True)
    args = parser.parse_args()

    summary = json.loads((ROOT / "results/e12_canonical_summary.json").read_text(encoding="utf-8"))
    from pyscipopt import Model
    model = Model()
    model.hideOutput(True)
    scip = ".".join(str(v) for v in (model.getMajorVersion(), model.getMinorVersion(), model.getTechVersion()))
    versions = {
        "qiskit": metadata.version("qiskit"),
        "qiskit_addon_cutting": metadata.version("qiskit-addon-cutting"),
        "qiskit_aer": metadata.version("qiskit-aer"),
        "scipy": metadata.version("scipy"),
        "pyscipopt": metadata.version("pyscipopt"),
        "kahip": metadata.version("kahip"),
        "mqt_bench": metadata.version("mqt.bench"),
        "mqt_qcec": metadata.version("mqt-qcec"),
        "mqt_core": metadata.version("mqt-core"),
        "nanobind_backend": metadata.version("nanobind-backend"),
        "matplotlib": metadata.version("matplotlib"),
        "pytest": metadata.version("pytest"),
        "scip": scip,
    }
    missing = [name for name in FILES if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f"release files missing: {missing}")
    manifest = {
        "manifest_schema": "certicut-release-v3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manuscript_title": "Representation Dependence of Optimal Cut Placement in Quasiprobability Circuit Cutting",
        "source_git_commit": git_head(),
        "source_tree_clean": not bool(git_status_porcelain()),
        "source_tree_changes": git_status_porcelain(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "versions": versions,
        "validation": {
            "pytest": {"passed": args.pytest_passed, "failed": 0},
            "latex_build": "pdflatex -> bibtex -> pdflatex -> pdflatex",
            "pdf_pages": args.pdf_pages,
            "environment_check": "reproducibility/verify_environment.py",
        },
        "canonical_e12": summary,
        "file_sha256": {name: sha256(ROOT / name) for name in FILES},
    }
    OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
