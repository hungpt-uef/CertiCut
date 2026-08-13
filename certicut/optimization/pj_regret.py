"""Tie-safe exhaustive independent-versus-parallel-joint model-regret oracle.

The supported joint model is deliberately narrow: the Schmitt--Piveteau--
Sutter parallel-layer policy for exact-balanced K=2 partitions only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp

from qiskit import QuantumCircuit

from certicut.optimization.parallel_joint import (
    evaluate_parallel_joint_partition,
    exact_balanced_partitions,
)


@dataclass(frozen=True)
class PJModelRegretResult:
    """Exact K=2 regret after minimizing over every independent-model tie."""

    num_qubits: int
    partition_count: int
    independent_optimum_log_cost: float
    parallel_joint_optimum_log_cost: float
    parallel_joint_at_best_independent_log_cost: float
    decision_regret_factor: float
    decision_delta_log_cost: float
    independent_optimum_count: int
    parallel_joint_optimum_count: int
    minimum_assignment_disagreement: int
    strict_model_reversal: bool
    independent_representative_partition: tuple[int, ...]
    parallel_joint_representative_partition: tuple[int, ...]

    def as_dict(self) -> dict:
        return asdict(self)


def exhaustive_pj_model_regret(circuit: QuantumCircuit, *, tolerance: float = 1e-10) -> PJModelRegretResult:
    """Compute the exact tie-safe decision regret for a balanced K=2 circuit.

    ``min_{P in argmin I} J(P)`` avoids attributing arbitrary independent-model
    tie breaking to the QPD model. Global label symmetry is already removed by
    fixing qubit zero to fragment zero.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    scored = tuple(
        (partition, evaluate_parallel_joint_partition(circuit, partition))
        for partition in exact_balanced_partitions(circuit.num_qubits)
    )
    if not scored:
        raise ValueError("exact PJ model-regret oracle requires a positive even qubit count")
    independent_optimum = min(score.independent_log_cost for _, score in scored)
    joint_optimum = min(score.parallel_joint_log_cost for _, score in scored)
    independent_ties = tuple(
        (partition, score)
        for partition, score in scored
        if score.independent_log_cost <= independent_optimum + tolerance
    )
    joint_ties = tuple(
        (partition, score)
        for partition, score in scored
        if score.parallel_joint_log_cost <= joint_optimum + tolerance
    )
    independent_representative, joint_at_independent = min(
        independent_ties, key=lambda item: (item[1].parallel_joint_log_cost, item[0])
    )
    joint_representative, _ = min(joint_ties, key=lambda item: item[0])
    delta = joint_at_independent.parallel_joint_log_cost - joint_optimum
    disagreement = min(
        sum(left != right for left, right in zip(independent_partition, joint_partition, strict=True))
        for independent_partition, _ in independent_ties
        for joint_partition, _ in joint_ties
    )
    return PJModelRegretResult(
        circuit.num_qubits,
        len(scored),
        independent_optimum,
        joint_optimum,
        joint_at_independent.parallel_joint_log_cost,
        exp(delta),
        delta,
        len(independent_ties),
        len(joint_ties),
        disagreement,
        delta > tolerance,
        independent_representative,
        joint_representative,
    )
