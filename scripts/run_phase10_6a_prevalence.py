"""Systematic small-corpus PJ-QPD reversal prevalence using exact pattern MILP."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random
from time import perf_counter

from qiskit import QuantumCircuit
from qiskit.circuit.library import RZZGate, iSwapGate

from certicut.optimization.parallel_joint import exact_balanced_partitions, evaluate_parallel_joint_partition
from certicut.optimization.pj_exact import solve_exact_pj_pattern_milp


ROOT = Path(__file__).resolve().parents[1]


def make_circuit(n: int, depth: int, seed: int, family: str) -> QuantumCircuit:
    rng = Random(seed)
    circuit = QuantumCircuit(n)
    for layer in range(depth):
        qubits = list(range(n))
        if family == "random_matching":
            rng.shuffle(qubits)
        elif family == "ring_even_odd":
            shift = layer % 2
            qubits = list(range(shift, n)) + list(range(shift))
        else:
            raise ValueError(f"unknown family {family}")
        for first, second in zip(qubits[::2], qubits[1::2], strict=True):
            if family == "random_matching":
                kind = rng.choice(("cx", "cx", "rzz", "iswap"))
            else:
                kind = "cx" if layer % 2 == 0 else "rzz"
            if kind == "cx":
                circuit.cx(first, second)
            elif kind == "rzz":
                circuit.append(RZZGate(rng.choice((0.1, 0.3, 0.7853981633974483))), (first, second))
            else:
                circuit.append(iSwapGate(), (first, second))
    return circuit


def independent_optimum(circuit: QuantumCircuit):
    candidates = [(p, evaluate_parallel_joint_partition(circuit, p)) for p in exact_balanced_partitions(circuit.num_qubits)]
    return min(candidates, key=lambda item: (item[1].independent_log_cost, item[0]))


def main() -> None:
    records = []
    for n in (8, 10, 12):
        for depth in (3, 5):
            for family in ("random_matching", "ring_even_odd"):
                for seed in range(5):
                    circuit = make_circuit(n, depth, 20261060 + 1000 * n + 100 * depth + seed, family)
                    started = perf_counter()
                    pj = solve_exact_pj_pattern_milp(circuit)
                    solver_s = perf_counter() - started
                    p_ind, ind_eval = independent_optimum(circuit)
                    pj_eval_ind = evaluate_parallel_joint_partition(circuit, p_ind)
                    strict_reversal = pj.partition != p_ind and pj_eval_ind.parallel_joint_log_cost > (pj.objective_log_cost or 0.0) + 1e-9
                    records.append({
                        "n": n, "depth": depth, "family": family, "seed": seed,
                        "status": pj.status, "solver_s": solver_s,
                        "independent_partition": p_ind, "pj_partition": pj.partition,
                        "independent_log_opt": ind_eval.independent_log_cost,
                        "pj_log_at_independent_opt": pj_eval_ind.parallel_joint_log_cost,
                        "pj_log_opt": pj.objective_log_cost,
                        "pj_regret_factor": pj_eval_ind.parallel_joint_overhead / (pj.overhead or 1.0),
                        "strict_reversal": strict_reversal,
                        "pattern_variables": pj.variable_count,
                    })
                    print(f"[{family} n={n} d={depth} seed={seed}] reversal={strict_reversal}; F={records[-1]['pj_regret_factor']:.4f}; t={solver_s:.3f}s")
    destination = ROOT / "results" / "phase10_6a_pj_prevalence.json"
    destination.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
