from __future__ import annotations

import platform
import sys
from importlib import metadata

EXPECTED = {
    "qiskit": "2.5.1",
    "qiskit-addon-cutting": "0.10.0",
    "qiskit-aer": "0.17.2",
    "scipy": "1.17.1",
    "pyscipopt": "6.2.1",
    "kahip": "3.25",
    "mqt.bench": "2.2.2",
    "mqt-qcec": "3.10.0",
    "mqt-core": "3.10.1",
    "nanobind-backend": "1.0.0",
    "matplotlib": "3.11.1",
    "pytest": "8.4.2",
}


def main() -> None:
    if sys.version_info[:3] != (3, 11, 9):
        raise SystemExit(f"Python mismatch: expected 3.11.9, got {platform.python_version()}")
    mismatches = []
    for package, expected in EXPECTED.items():
        actual = metadata.version(package)
        if actual != expected:
            mismatches.append((package, expected, actual))
    from pyscipopt import Model
    model = Model()
    model.hideOutput(True)
    scip_version = ".".join(
        str(v) for v in (model.getMajorVersion(), model.getMinorVersion(), model.getTechVersion())
    )
    if scip_version != "10.0.2":
        mismatches.append(("SCIP", "10.0.2", scip_version))
    if mismatches:
        for package, expected, actual in mismatches:
            print(f"{package}: expected {expected}, got {actual}")
        raise SystemExit(1)
    print(f"Python {platform.python_version()}")
    print(f"Platform {platform.platform()}")
    print(f"SCIP {scip_version}")
    print("All pinned research dependencies match the reference release.")


if __name__ == "__main__":
    main()
