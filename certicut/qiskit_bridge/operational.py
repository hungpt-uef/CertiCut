"""Execute CertiCut gate plans through Qiskit QPD cutting and exact reconstruction."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, fsum, isfinite, log, sqrt
from typing import Any, Sequence

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import PauliList, Statevector
from qiskit_addon_cutting import cut_gates, generate_cutting_experiments, partition_problem, reconstruct_expectation_values
from qiskit_addon_cutting.utils.simulation import ExactSampler
from qiskit_aer.primitives import SamplerV2

from certicut.graph.interaction import InteractionGraph
from certicut.optimization.exact import ExactSolution


@dataclass(frozen=True)
class OperationalValidation:
    partition: tuple[int, ...]
    cut_instruction_indices: tuple[int, ...]
    optimizer_log_cost: float
    qpd_log_overhead: float
    qpd_overhead: float | None
    uncut_expectation: float
    reconstructed_expectation: float
    absolute_error: float
    fragment_experiment_counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FiniteShotObservableValidation:
    """Finite-shot distribution for one Pauli observable and one cut plan."""

    observable: str
    uncut_expectation: float
    estimator_distribution: tuple[float, ...]
    estimator_mean: float
    bias: float
    rmse: float
    estimator_standard_deviation: float


@dataclass(frozen=True)
class FiniteShotPlanValidation:
    """Finite-shot reconstruction summary for one exact balanced cut plan."""

    partition: tuple[int, ...]
    cut_instruction_indices: tuple[int, ...]
    optimizer_log_cost: float
    qpd_log_overhead: float
    qpd_overhead: float | None
    total_shots_per_seed: int
    qpd_samples_per_seed: int
    seeds: tuple[int, ...]
    trial_shot_totals: tuple[int, ...]
    trial_fragment_experiment_counts: tuple[dict[str, int], ...]
    observables: tuple[FiniteShotObservableValidation, ...]


@dataclass(frozen=True)
class FiniteShotComparison:
    """Like-for-like finite-shot validation of exactly two balanced cut plans."""

    total_shots_per_seed: int
    qpd_samples_per_seed: int
    seeds: tuple[int, ...]
    plans: tuple[FiniteShotPlanValidation, FiniteShotPlanValidation]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_exact_reconstruction(
    circuit: QuantumCircuit, graph: InteractionGraph, solution: ExactSolution
) -> OperationalValidation:
    """Execute the selected cut plan exactly and compare all-Z expectation to uncut statevector."""
    if solution.partition is None or solution.objective_log_cost is None:
        raise ValueError("operational validation requires a feasible solution")
    if tuple(solution.cut_instruction_indices) != tuple(
        index for edge in graph.edges if solution.partition[edge.u] != solution.partition[edge.v] for index in edge.instruction_indices
    ):
        raise ValueError("solution cut metadata does not match graph partition")
    observable = PauliList(["Z" * circuit.num_qubits])
    uncut = float(Statevector(circuit).expectation_value(observable[0]).real)
    cut_circuit, bases = cut_gates(circuit, list(solution.cut_instruction_indices))
    problem = partition_problem(cut_circuit, list(solution.partition), observable)
    experiments, coefficients = generate_cutting_experiments(problem.subcircuits, problem.subobservables, float("inf"))
    sampler = ExactSampler()
    results = {label: sampler.run(subcircuits).result() for label, subcircuits in experiments.items()}
    reconstructed = float(reconstruct_expectation_values(results, coefficients, problem.subobservables)[0])
    qpd_log = sum(log(float(basis.overhead)) for basis in bases)
    return OperationalValidation(
        partition=solution.partition,
        cut_instruction_indices=solution.cut_instruction_indices,
        optimizer_log_cost=solution.objective_log_cost,
        qpd_log_overhead=qpd_log,
        qpd_overhead=exp(qpd_log) if qpd_log < log(float.fromhex("0x1.fffffffffffffp+1023")) else None,
        uncut_expectation=uncut,
        reconstructed_expectation=reconstructed,
        absolute_error=abs(uncut - reconstructed),
        fragment_experiment_counts={str(label): len(subcircuits) for label, subcircuits in experiments.items()},
    )


def validate_finite_shot_comparison(
    circuit: QuantumCircuit,
    graph: InteractionGraph,
    solutions: Sequence[ExactSolution],
    *,
    total_shots_per_seed: int,
    qpd_samples_per_seed: int,
    seeds: Sequence[int],
    observables: PauliList | Sequence[str] | None = None,
) -> FiniteShotComparison:
    """Compare exactly two balanced cut plans with equal finite-shot budgets.

    Each seed controls both Addon Cutting QPD sampling and Aer measurement sampling.
    ``total_shots_per_seed`` is split across all generated fragment experiments,
    so each plan receives exactly the same total number of circuit shots per seed.
    """
    plans = tuple(solutions)
    if len(plans) != 2:
        raise ValueError("finite-shot comparison requires exactly two cut plans")
    if total_shots_per_seed < 1:
        raise ValueError("total_shots_per_seed must be positive")
    if qpd_samples_per_seed < 1:
        raise ValueError("qpd_samples_per_seed must be positive")
    trial_seeds = tuple(seeds)
    if not trial_seeds:
        raise ValueError("at least one deterministic seed is required")
    if len(set(trial_seeds)) != len(trial_seeds):
        raise ValueError("seeds must be unique")
    for solution in plans:
        _validate_balanced_cut_plan(circuit, graph, solution)
    paulis = _normalize_observables(circuit, observables)
    references = tuple(float(Statevector(circuit).expectation_value(pauli).real) for pauli in paulis)
    validations = tuple(
        _validate_finite_shot_plan(
            circuit,
            plan,
            paulis,
            references,
            total_shots_per_seed,
            qpd_samples_per_seed,
            trial_seeds,
        )
        for plan in plans
    )
    return FiniteShotComparison(
        total_shots_per_seed=total_shots_per_seed,
        qpd_samples_per_seed=qpd_samples_per_seed,
        seeds=trial_seeds,
        plans=(validations[0], validations[1]),
    )


def _validate_balanced_cut_plan(
    circuit: QuantumCircuit, graph: InteractionGraph, solution: ExactSolution
) -> None:
    if solution.partition is None or solution.objective_log_cost is None:
        raise ValueError("operational validation requires a feasible solution")
    if solution.num_fragments != 2 or not solution.exact_num_fragments:
        raise ValueError("finite-shot comparison requires exact two-fragment plans")
    if solution.qmax != (circuit.num_qubits + 1) // 2:
        raise ValueError("finite-shot comparison requires exact balanced capacity")
    sizes = tuple(solution.partition.count(label) for label in range(2))
    if tuple(sorted(sizes)) != (circuit.num_qubits // 2, (circuit.num_qubits + 1) // 2):
        raise ValueError("solution partition is not balanced")
    if tuple(solution.cut_instruction_indices) != tuple(
        index
        for edge in graph.edges
        if solution.partition[edge.u] != solution.partition[edge.v]
        for index in edge.instruction_indices
    ):
        raise ValueError("solution cut metadata does not match graph partition")


def _normalize_observables(
    circuit: QuantumCircuit, observables: PauliList | Sequence[str] | None
) -> PauliList:
    paulis = PauliList(["Z" * circuit.num_qubits]) if observables is None else PauliList(observables)
    if len(paulis) == 0:
        raise ValueError("at least one observable is required")
    if paulis.num_qubits != circuit.num_qubits:
        raise ValueError("observable width must equal circuit width")
    if any(pauli.phase != 0 for pauli in paulis):
        raise ValueError("observables must have phase 1")
    return paulis


def _validate_finite_shot_plan(
    circuit: QuantumCircuit,
    solution: ExactSolution,
    observables: PauliList,
    references: tuple[float, ...],
    total_shots: int,
    qpd_samples: int,
    seeds: tuple[int, ...],
) -> FiniteShotPlanValidation:
    estimates = [[] for _ in observables]
    trial_shot_totals = []
    trial_counts = []
    for seed in seeds:
        current, shot_total, counts = _run_finite_shot_trial(
            circuit, solution, observables, total_shots, qpd_samples, seed
        )
        for values, estimate in zip(estimates, current):
            values.append(estimate)
        trial_shot_totals.append(shot_total)
        trial_counts.append(counts)
    observable_summaries = tuple(
        _summarize_finite_shot_observable(str(pauli), reference, tuple(values))
        for pauli, reference, values in zip(observables, references, estimates)
    )
    cut_circuit, bases = cut_gates(circuit, list(solution.cut_instruction_indices))
    qpd_log = sum(log(float(basis.overhead)) for basis in bases)
    return FiniteShotPlanValidation(
        partition=solution.partition,
        cut_instruction_indices=solution.cut_instruction_indices,
        optimizer_log_cost=solution.objective_log_cost,
        qpd_log_overhead=qpd_log,
        qpd_overhead=exp(qpd_log) if qpd_log < log(float.fromhex("0x1.fffffffffffffp+1023")) else None,
        total_shots_per_seed=total_shots,
        qpd_samples_per_seed=qpd_samples,
        seeds=seeds,
        trial_shot_totals=tuple(trial_shot_totals),
        trial_fragment_experiment_counts=tuple(trial_counts),
        observables=observable_summaries,
    )


def _run_finite_shot_trial(
    circuit: QuantumCircuit,
    solution: ExactSolution,
    observables: PauliList,
    total_shots: int,
    qpd_samples: int,
    seed: int,
) -> tuple[tuple[float, ...], int, dict[str, int]]:
    cut_circuit, _ = cut_gates(circuit, list(solution.cut_instruction_indices))
    problem = partition_problem(cut_circuit, list(solution.partition), observables)
    # Addon Cutting's QPD sampler uses NumPy's legacy global RNG.
    state = np.random.get_state()
    try:
        np.random.seed(seed)
        experiments, coefficients = generate_cutting_experiments(
            problem.subcircuits, problem.subobservables, qpd_samples
        )
    finally:
        np.random.set_state(state)
    flat_experiments = [experiment for group in experiments.values() for experiment in group]
    if total_shots < len(flat_experiments):
        raise ValueError(
            "total_shots_per_seed is smaller than the generated fragment experiment count "
            f"({total_shots} < {len(flat_experiments)})"
        )
    base, remainder = divmod(total_shots, len(flat_experiments))
    shots = tuple(base + (index < remainder) for index in range(len(flat_experiments)))
    sampler = SamplerV2(seed=seed)
    offset = 0
    results = {}
    for label, group in experiments.items():
        group_shots = shots[offset : offset + len(group)]
        # Aer does not natively assemble every supported Qiskit two-qubit gate.
        # Transpile only generated local fragment experiments, after QPD sampling.
        group = transpile(group, basis_gates=["rz", "sx", "x", "cx", "measure"], optimization_level=0)
        results[label] = sampler.run(
            [(experiment, None, shots) for experiment, shots in zip(group, group_shots)]
        ).result()
        offset += len(group)
    return (
        tuple(float(value) for value in reconstruct_expectation_values(results, coefficients, problem.subobservables)),
        sum(shots),
        {str(label): len(group) for label, group in experiments.items()},
    )


def _summarize_finite_shot_observable(
    observable: str, reference: float, estimates: tuple[float, ...]
) -> FiniteShotObservableValidation:
    mean = fsum(estimates) / len(estimates)
    bias = mean - reference
    rmse = sqrt(fsum((estimate - reference) ** 2 for estimate in estimates) / len(estimates))
    standard_deviation = sqrt(fsum((estimate - mean) ** 2 for estimate in estimates) / len(estimates))
    return FiniteShotObservableValidation(
        observable=observable,
        uncut_expectation=reference,
        estimator_distribution=estimates,
        estimator_mean=mean,
        bias=bias,
        rmse=rmse,
        estimator_standard_deviation=standard_deviation,
    )
