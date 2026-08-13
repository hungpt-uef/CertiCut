"""E11: exact, tie-safe independent-QPD versus parallel-joint-QPD regret study.

Scope: exact-balanced K=2 only. The joint policy is legal parallel-layer QPD;
it is not a general K-way, temporal, or wire-cut objective.
"""

from __future__ import annotations

import json
from math import pi
from pathlib import Path
from random import Random
from time import perf_counter

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, iSwapGate

from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.optimization.pj_regret import exhaustive_pj_model_regret


ROOT = Path(__file__).resolve().parents[1]


def make_layered_circuit(n: int, depth: int, seed: int, family: str) -> QuantumCircuit:
    """Build deterministic disjoint two-qubit layers with heterogeneous QPD costs."""
    rng = Random(seed)
    circuit = QuantumCircuit(n)
    for layer in range(depth):
        qubits = list(range(n))
        if family == "random_matching":
            rng.shuffle(qubits)
        elif family == "ring_even_odd":
            qubits = list(range(layer % 2, n)) + list(range(layer % 2))
        else:
            raise ValueError(f"unknown family {family}")
        for first, second in zip(qubits[::2], qubits[1::2], strict=True):
            gate = rng.choice(("cx", "cx", "rzz", "iswap")) if family == "random_matching" else ("cx" if layer % 2 == 0 else "rzz")
            if gate == "cx":
                circuit.cx(first, second)
            elif gate == "rzz":
                circuit.append(RZZGate(rng.choice((0.1, 0.3, pi / 4))), (first, second))
            else:
                circuit.append(iSwapGate(), (first, second))
    return circuit


def known_reversal_witness() -> QuantumCircuit:
    """Frozen Phase 10.5 witness; validates E11 detects a real model reversal."""
    circuit = QuantumCircuit(6)
    circuit.iswap(5, 1)
    circuit.cx(0, 3)
    circuit.cx(4, 2)
    circuit.cx(3, 4)
    circuit.rzz(0.3, 2, 1)
    circuit.iswap(0, 5)
    circuit.rzz(pi / 4, 0, 4)
    circuit.rzz(pi / 4, 2, 5)
    circuit.iswap(3, 1)
    return circuit


def _record(source: str, representation: str, family: str, n: int, seed: int, circuit: QuantumCircuit, audit: dict | None) -> dict:
    started = perf_counter()
    result = exhaustive_pj_model_regret(circuit)
    return {
        "source": source,
        "representation": representation,
        "family": family,
        "n": n,
        "seed": seed,
        "two_qubit_gate_count": sum(item.operation.num_qubits == 2 for item in circuit.data),
        "runtime_s": perf_counter() - started,
        "audit": audit,
        **result.as_dict(),
    }


def main() -> None:
    records: list[dict] = []
    witness = known_reversal_witness()
    records.append(_record("controlled", "native", "known_reversal_witness", witness.num_qubits, 29, witness, None))
    for n in (8, 10, 12):
        for depth in (3, 5):
            for family in ("random_matching", "ring_even_odd"):
                for seed in range(5):
                    circuit = make_layered_circuit(n, depth, 20260812 + 1000 * n + 100 * depth + seed, family)
                    records.append(_record("synthetic", "native", family, n, seed, circuit, None))
    for family in ("qaoa", "qft", "draper_qft_adder"):
        for n in (8, 10):
            try:
                paired = ingest_mqt_pair(family, n)
            except Exception as error:
                records.append({"source": "mqt", "family": family, "n": n, "status": "ingestion_error", "error": repr(error)})
                continue
            for representation, (circuit, audit) in paired.items():
                records.append(_record("mqt", representation, family, n, 0, circuit, audit.as_dict()))
    output = ROOT / "results" / "e11_exact_model_regret.json"
    output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    valid = [record for record in records if "decision_regret_factor" in record]
    reversals = [record for record in valid if record["strict_model_reversal"]]
    print(json.dumps({
        "records": len(records), "valid": len(valid), "strict_reversals": len(reversals),
        "maximum_decision_regret": max((record["decision_regret_factor"] for record in valid), default=None),
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
