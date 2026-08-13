"""Validate PJ-QPD closed-form layer objective against generated theorem decompositions."""

from __future__ import annotations

import json
from math import isclose
from pathlib import Path
from random import Random

from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, RZZGate, iSwapGate

from certicut.costs.joint_parallel import build_schmitt_parallel_decomposition
from certicut.optimization.parallel_joint import evaluate_parallel_joint_partition


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    rng = Random(20261051)
    records = []
    for case_id in range(100):
        width = rng.choice((2, 4, 6))
        circuit = QuantumCircuit(width)
        partition = tuple(0 if qubit < width // 2 else 1 for qubit in range(width))
        operations = ("cx", "rzz", "iswap")
        for first in range(width // 2):
            second = first + width // 2
            kind = rng.choice(operations)
            if kind == "cx":
                circuit.cx(first, second)
            elif kind == "rzz":
                circuit.append(RZZGate(rng.choice((0.1, 0.3, 0.7853981633974483))), (first, second))
            else:
                circuit.append(iSwapGate(), (first, second))
        generated = build_schmitt_parallel_decomposition(circuit, tuple(range(width // 2)), tuple(range(width // 2)))
        formula = evaluate_parallel_joint_partition(circuit, partition)
        records.append({
            "case_id": case_id,
            "width": width,
            "formula_log": formula.parallel_joint_log_cost,
            "generated_log": generated.log_sampling_overhead,
            "abs_error": abs(formula.parallel_joint_log_cost - generated.log_sampling_overhead),
            "formula_overhead": formula.parallel_joint_overhead,
            "generated_overhead": generated.sampling_overhead,
        })
    assert all(record["abs_error"] < 1e-10 for record in records)
    destination = ROOT / "results" / "phase10_5_formula_generated_validation.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Validated {len(records)}/{len(records)} layers; max error={max(r['abs_error'] for r in records):.3e}")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
