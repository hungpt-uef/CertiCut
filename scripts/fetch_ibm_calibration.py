"""Fetch, validate, and freeze a Qiskit IBM Runtime backend calibration snapshot."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import qiskit_ibm_runtime


ROOT = Path(__file__).resolve().parents[1]


def _instruction_error(properties: Any, operation: str, qubits: tuple[int, ...]) -> float | None:
    """Read an instruction error defensively across Qiskit Target property shapes."""
    try:
        target_entry = properties.target[operation][qubits]
        error = getattr(target_entry, "error", None)
        return float(error) if error is not None else None
    except (KeyError, TypeError, AttributeError):
        return None


def _snapshot_from_backend(backend: Any, *, source: str) -> dict[str, Any]:
    """Extract a JSON-serializable target snapshot from a live or official fake backend."""
    target = backend.target
    physical_qubits = tuple(range(backend.num_qubits))
    coupling = sorted({tuple(sorted(edge)) for edge in backend.coupling_map.get_edges()})
    readout = {
        str(qubit): error
        for qubit in physical_qubits
        if (error := _instruction_error(backend, "measure", (qubit,))) is not None
    }
    gate_errors: dict[str, float] = {}
    for name in target.operation_names:
        qargs = target.qargs_for_operation_name(name) or ()
        for qubits in qargs:
            if len(qubits) != 2:
                continue
            error = _instruction_error(backend, name, tuple(qubits))
            if error is not None:
                gate_errors[f"{name}:{qubits[0]},{qubits[1]}"] = error
    return {
        "schema_version": 1,
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "backend_name": backend.name,
        "backend_version": getattr(backend, "backend_version", None),
        "num_qubits": backend.num_qubits,
        "physical_qubits": physical_qubits,
        "coupling_edges": coupling,
        "readout_errors": readout,
        "two_qubit_gate_errors": gate_errors,
        "source": source,
        "qiskit_ibm_runtime_version": qiskit_ibm_runtime.__version__,
    }


def snapshot_backend(backend_name: str, token: str) -> dict[str, Any]:
    """Return a JSON-serializable immutable calibration payload from IBM Runtime."""
    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
    return _snapshot_from_backend(service.backend(backend_name), source="qiskit_ibm_runtime_live")


def snapshot_fake_backend(backend_name: str) -> dict[str, Any]:
    """Freeze an official Qiskit IBM Runtime FakeBackend without credentials or network access."""
    from qiskit_ibm_runtime import fake_provider

    classes = {
        "ibm_brisbane": fake_provider.FakeBrisbane,
        "ibm_kyoto": fake_provider.FakeKyoto,
        "ibm_sherbrooke": fake_provider.FakeSherbrooke,
    }
    return _snapshot_from_backend(
        classes[backend_name](), source="qiskit_ibm_runtime_fake_provider"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("ibm_brisbane", "ibm_kyoto", "ibm_sherbrooke"), default="ibm_brisbane")
    parser.add_argument("--source", choices=("live", "fake"), default="fake")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "fixtures")
    args = parser.parse_args()
    if args.source == "live":
        token = os.environ.get("QISKIT_IBM_TOKEN")
        if not token:
            raise SystemExit("QISKIT_IBM_TOKEN is required for --source live; no calibration fixture was written.")
        snapshot = snapshot_backend(args.backend, token)
    else:
        snapshot = snapshot_fake_backend(args.backend)
    payload = json.dumps(snapshot, sort_keys=True, indent=2).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    snapshot["sha256"] = digest
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = snapshot["fetched_at_utc"].replace(":", "").replace("+00:00", "Z").replace("-", "")[:15]
    suffix = "fake_calib" if args.source == "fake" else "calib"
    destination = args.out_dir / f"{args.backend}_{suffix}_{stamp}.json"
    destination.write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
