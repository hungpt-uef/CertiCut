"""Exact QPD checks and a brute-force six-qubit cutting baseline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
from math import log
from typing import Any

from qiskit import QuantumCircuit
from qiskit.quantum_info import PauliList, Statevector
from qiskit_addon_cutting import (
    cut_gates,
    generate_cutting_experiments,
    partition_problem,
    reconstruct_expectation_values,
)
from qiskit_addon_cutting.utils.simulation import ExactSampler


CNOT_CUT_OVERHEAD = 9.0


@dataclass(frozen=True)
class CutPlan:
    """A two-fragment plan evaluated with independent CNOT-cut cost."""

    fragments: tuple[tuple[int, ...], tuple[int, ...]]
    cut_gate_indices: tuple[int, ...]
    gamma: float
    log_cost: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def cnot_sampling_overhead(cut_count: int) -> float:
    """Return Gamma for independently decomposed CNOT cuts."""
    if cut_count < 0:
        raise ValueError("cut_count must be non-negative")
    return CNOT_CUT_OVERHEAD**cut_count


def make_bell_cnot_circuit(cut_count: int) -> tuple[QuantumCircuit, list[int]]:
    """Create one or two Bell-pair CNOTs and return their instruction IDs."""
    if cut_count not in (1, 2):
        raise ValueError("Phase 0 supports one or two CNOT cuts")

    circuit = QuantumCircuit(2 * cut_count)
    gate_ids = []
    for pair in range(cut_count):
        control = 2 * pair
        circuit.h(control)
        circuit.cx(control, control + 1)
        gate_ids.append(len(circuit.data) - 1)
    return circuit, gate_ids


def reconstruct_cut_z_expectation(cut_count: int) -> dict[str, float | int]:
    """Reconstruct the exact all-Z expectation from separated CNOT cuts."""
    circuit, gate_ids = make_bell_cnot_circuit(cut_count)
    observable = PauliList(["Z" * circuit.num_qubits])
    uncut_expectation = Statevector(circuit).expectation_value(observable[0]).real
    cut_circuit, bases = cut_gates(circuit, gate_ids)
    labels = list(range(circuit.num_qubits))
    problem = partition_problem(cut_circuit, labels, observable)
    experiments, coefficients = generate_cutting_experiments(
        problem.subcircuits, problem.subobservables, float("inf")
    )
    sampler = ExactSampler()
    results = {label: sampler.run(subcircuits).result() for label, subcircuits in experiments.items()}
    expectation = reconstruct_expectation_values(
        results, coefficients, problem.subobservables
    )[0]
    qpd_overhead = 1.0
    for basis in bases:
        qpd_overhead *= basis.kappa**2
    return {
        "cut_count": cut_count,
        "qpd_overhead": float(qpd_overhead),
        "expected_overhead": cnot_sampling_overhead(cut_count),
        "uncut_z_expectation": float(uncut_expectation),
        "reconstructed_z_expectation": float(expectation),
        "subexperiment_count_per_fragment": len(next(iter(experiments.values()))),
    }


def make_six_qubit_toy_circuit() -> QuantumCircuit:
    """Create the handbook's 3+3 toy circuit with two intended crossing CNOTs."""
    circuit = QuantumCircuit(6)
    for control, target in ((0, 1), (1, 2), (3, 4), (4, 5), (1, 4), (2, 3)):
        circuit.cx(control, target)
    return circuit


def brute_force_two_fragment_plan(circuit: QuantumCircuit, qmax: int) -> CutPlan:
    """Enumerate every valid two-fragment partition, fixing q0 to break symmetry."""
    if circuit.num_qubits < 2:
        raise ValueError("at least two qubits are required")
    if circuit.num_qubits > 2 * qmax:
        raise ValueError("two fragments cannot satisfy qmax")

    qubits = tuple(range(circuit.num_qubits))
    candidates: list[CutPlan] = []
    for size in range(1, qmax + 1):
        for remainder in combinations(qubits[1:], size - 1):
            first = (0, *remainder)
            second = tuple(qubit for qubit in qubits if qubit not in first)
            if not second or len(second) > qmax:
                continue
            first_set = set(first)
            cut_gate_indices = tuple(
                gate_index
                for gate_index, instruction in enumerate(circuit.data)
                if instruction.operation.num_qubits == 2
                and ((circuit.find_bit(instruction.qubits[0]).index in first_set)
                     != (circuit.find_bit(instruction.qubits[1]).index in first_set))
            )
            gamma = cnot_sampling_overhead(len(cut_gate_indices))
            candidates.append(
                CutPlan(
                    fragments=(tuple(sorted(first)), second),
                    cut_gate_indices=cut_gate_indices,
                    gamma=gamma,
                    log_cost=log(gamma),
                )
            )
    if not candidates:
        raise ValueError("no valid two-fragment partition")
    return min(candidates, key=lambda plan: (plan.log_cost, plan.fragments))


def phase0_summary() -> dict[str, Any]:
    """Return deterministic Phase 0 results for JSON output and tests."""
    toy_plan = brute_force_two_fragment_plan(make_six_qubit_toy_circuit(), qmax=3)
    return {
        "manual_cnot_cuts": [
            reconstruct_cut_z_expectation(1),
            reconstruct_cut_z_expectation(2),
        ],
        "six_qubit_toy": toy_plan.as_dict(),
    }
