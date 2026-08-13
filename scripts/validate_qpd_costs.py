"""Emit Qiskit QPD cost-registry validation artifact."""

from __future__ import annotations

import json
from math import pi, sin, sqrt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qiskit.circuit.library import CSGate, CXGate, CZGate, DCXGate, RXXGate, RZZGate, iSwapGate
import qiskit_addon_cutting

from certicut.costs.qpd import qpd_cost


def main() -> None:
    cases = [
        ("cx", CXGate(), 9.0), ("cz", CZGate(), 9.0), ("cs", CSGate(), 3 + 2 * sqrt(2)),
        ("iswap", iSwapGate(), 49.0), ("dcx", DCXGate(), 49.0),
        ("rzz_0", RZZGate(0), 1.0),
        ("rzz_pi_4", RZZGate(pi / 4), (1 + 2 * abs(sin(pi / 4))) ** 2),
        ("rzz_pi_2", RZZGate(pi / 2), 9.0),
        ("rxx_pi_4", RXXGate(pi / 4), (1 + 2 * abs(sin(pi / 4))) ** 2),
    ]
    output = {"qiskit_addon_cutting_version": qiskit_addon_cutting.__version__, "model": "independent_qiskit_qpd_0.10.0", "cases": []}
    for name, gate, expected in cases:
        cost = qpd_cost(gate)
        output["cases"].append({"gate": name, "params": cost.gate_params, "overhead": cost.overhead, "expected": expected, "log_cost": cost.log_cost, "source": cost.source, "pass": abs(cost.overhead - expected) <= 1e-10})
    Path("results/qpd_cost_registry_validation.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
