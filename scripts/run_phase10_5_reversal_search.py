"""Phase 10.5 exhaustive search for independent-QPD versus PJ-QPD partition reversals."""

from __future__ import annotations

import json
from dataclasses import asdict
from itertools import combinations
from math import exp
from pathlib import Path
from random import Random

from qiskit import QuantumCircuit
from qiskit.circuit.library import CXGate, RZZGate, iSwapGate

from certicut.optimization.parallel_joint import exact_balanced_partitions, evaluate_parallel_joint_partition


ROOT = Path(__file__).resolve().parents[1]


def random_layered_matching(seed: int, n: int, depth: int) -> QuantumCircuit:
    rng = Random(seed)
    circuit = QuantumCircuit(n)
    gate_pool = ("cx", "cx", "rzz", "iswap")
    for _ in range(depth):
        qubits = list(range(n))
        rng.shuffle(qubits)
        for first, second in zip(qubits[::2], qubits[1::2], strict=True):
            kind = rng.choice(gate_pool)
            if kind == "cx":
                circuit.cx(first, second)
            elif kind == "rzz":
                circuit.append(RZZGate(rng.choice((0.1, 0.3, 0.7853981633974483))), (first, second))
            else:
                circuit.append(iSwapGate(), (first, second))
    return circuit


def find_reversal() -> dict:
    for n in (6, 8, 10, 12):
        partitions = exact_balanced_partitions(n)
        for seed in range(300):
            circuit = random_layered_matching(20261050 + 1000 * n + seed, n, depth=3)
            scored = [(partition, evaluate_parallel_joint_partition(circuit, partition)) for partition in partitions]
            independent_best = min(score.independent_log_cost for _, score in scored)
            pj_best = min(score.parallel_joint_log_cost for _, score in scored)
            p_ind, eval_ind = next(
                (partition, score)
                for partition, score in scored
                if abs(score.independent_log_cost - independent_best) < 1e-12
                and score.parallel_joint_log_cost > pj_best + 1e-9
            ) if any(
                abs(score.independent_log_cost - independent_best) < 1e-12
                and score.parallel_joint_log_cost > pj_best + 1e-9
                for _, score in scored
            ) else (None, None)
            if p_ind is None:
                continue
            p_pj, eval_pj = next(
                (partition, score)
                for partition, score in scored
                if abs(score.parallel_joint_log_cost - pj_best) < 1e-12
            )
            if p_ind == p_pj:
                continue
            return {
                "num_qubits": n,
                "seed": seed,
                "depth": 3,
                "instructions": [
                    {"name": instruction.operation.name, "qubits": [circuit.find_bit(q).index for q in instruction.qubits], "params": [float(p) for p in instruction.operation.params]}
                    for instruction in circuit.data if instruction.operation.num_qubits == 2
                ],
                "independent_opt_partition": p_ind,
                "pj_opt_partition": p_pj,
                "independent_opt": asdict(eval_ind),
                "pj_opt": asdict(eval_pj),
                "pj_regret_log": eval_ind.parallel_joint_log_cost - eval_pj.parallel_joint_log_cost,
                "pj_regret_factor": exp(eval_ind.parallel_joint_log_cost - eval_pj.parallel_joint_log_cost),
            }
    raise RuntimeError("no strict independent-to-PJ reversal found in the configured deterministic search")


def main() -> None:
    witness = find_reversal()
    destination = ROOT / "results" / "phase10_5_partition_reversal_witness.json"
    destination.write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(witness, indent=2))
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
