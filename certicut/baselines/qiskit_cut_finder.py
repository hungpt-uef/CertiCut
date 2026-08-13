"""Track B Qiskit automatic gate-cut finder adapter; not exact-K comparable."""

from __future__ import annotations

from math import log
from time import perf_counter

from qiskit import QuantumCircuit
from qiskit_addon_cutting import DeviceConstraints, find_cuts
from qiskit_addon_cutting.automated_cut_finding import OptimizationParameters

from certicut.baselines.common import BaselineResult


def find_gate_only_cuts(
    circuit: QuantumCircuit, *, qmax: int, seed: int = 0,
    max_backjumps: int | None = None, max_gamma: float = float("inf"),
) -> BaselineResult:
    """Run Qiskit 0.10 automatic finder with gate cuts enabled and wire cuts disabled."""
    started = perf_counter()
    cut_circuit, metadata = find_cuts(
        circuit,
        OptimizationParameters(seed=seed, gate_lo=True, wire_lo=False, max_backjumps=max_backjumps, max_gamma=max_gamma),
        DeviceConstraints(qubits_per_subcircuit=qmax),
    )
    runtime = perf_counter() - started
    cuts = tuple(int(index) for cut_type, index in metadata["cuts"] if cut_type == "Gate Cut")
    if len(cuts) != len(metadata["cuts"]):
        raise RuntimeError("gate-only Qiskit configuration returned a non-gate cut")
    overhead = float(metadata["sampling_overhead"])
    return BaselineResult(
        "qiskit_gate_only", "B_practical_qmax", "feasible", runtime, log(overhead), overhead, cuts,
        _fragment_sizes(cut_circuit), bool(metadata["minimum_reached"]),
        "Track B only: Qiskit enforces maximum subcircuit width, not CertiCut exact balanced K=2 semantics.",
    )


def qiskit_track_b_record(
    circuit: QuantumCircuit, *, qmax: int, seed: int = 0,
    max_backjumps: int | None = None, max_gamma: float = float("inf"),
    track_a_optimum_log: float | None = None,
) -> dict:
    """Return full practical-Qmax metadata, with direct objective comparison only on overlap."""
    result = find_gate_only_cuts(
        circuit, qmax=qmax, seed=seed, max_backjumps=max_backjumps, max_gamma=max_gamma
    )
    fragments = result.fragment_sizes
    expected = tuple(sorted((circuit.num_qubits // 2, (circuit.num_qubits + 1) // 2)))
    overlap = len(fragments) == 2 and tuple(sorted(fragments)) == expected
    return {
        **result.as_dict(),
        "qiskit_seed": seed,
        "qiskit_max_backjumps": max_backjumps,
        "qiskit_max_gamma": "inf" if max_gamma == float("inf") else max_gamma,
        "num_gate_cuts": len(result.cut_instruction_indices),
        "num_fragments": len(fragments),
        "max_fragment_size": max(fragments, default=0),
        "qmax_requested": qmax,
        "track_a_overlap": overlap,
        "certicut_track_a_optimum_log": track_a_optimum_log if overlap else None,
        "objective_difference": (result.objective_log_cost - track_a_optimum_log) if overlap and track_a_optimum_log is not None else None,
    }


def _fragment_sizes(circuit: QuantumCircuit) -> tuple[int, ...]:
    components = [{qubit} for qubit in range(circuit.num_qubits)]
    for instruction in circuit.data:
        if instruction.operation.num_qubits != 2 or instruction.operation.name == "qpd_2q":
            continue
        indices = {circuit.find_bit(qubit).index for qubit in instruction.qubits}
        joined = set().union(*(component for component in components if component & indices))
        components = [component for component in components if not component & indices]
        components.append(joined)
    return tuple(sorted(len(component) for component in components))
