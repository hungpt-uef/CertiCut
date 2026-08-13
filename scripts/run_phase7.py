"""Operational exact QPD reconstruction for CertiCut-selected QAOA/VQE plans."""

from __future__ import annotations

import json
from math import pi
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate

from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.exact import solve_exact_partition
from certicut.qiskit_bridge.operational import validate_exact_reconstruction


def _qaoa() -> tuple[QuantumCircuit, str]:
    circuit = QuantumCircuit(6)
    for qubit in range(6):
        circuit.h(qubit)
        circuit.rx(pi / 6, qubit)
    for qubit in range(6):
        circuit.append(RZZGate(pi / 4), [qubit, (qubit + 1) % 6])
    return circuit, "native_qaoa_rzz_n6"


def _vqe() -> tuple[QuantumCircuit, str]:
    circuit = QuantumCircuit(6)
    for qubit in range(6):
        circuit.ry(pi / 4, qubit)
    for qubit in range(5):
        circuit.cx(qubit, qubit + 1)
    for qubit in range(6):
        circuit.ry(pi / 6, qubit)
    return circuit, "vqe_cx_n6"


def main() -> None:
    outputs = []
    for factory in (_qaoa, _vqe):
        circuit, name = factory()
        graph = build_interaction_graph(circuit, cost_model="qiskit_qpd")
        solution = solve_exact_partition(graph, num_fragments=2, qmax=3, exact_num_fragments=True)
        validation = validate_exact_reconstruction(circuit, graph, solution)
        outputs.append({"circuit": name, "cost_model": "qiskit_qpd_0.10_independent", "solution": solution.as_dict(), "validation": validation.as_dict()})
    Path("results/phase7_operational_validation.json").write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(outputs, indent=2))


if __name__ == "__main__":
    main()
