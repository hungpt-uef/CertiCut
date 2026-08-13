"""Search a small nonnegative weighted CP0/C/T/CT strictness witness."""

from __future__ import annotations

import random
import sys
from pathlib import Path
from itertools import product

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certicut.graph.interaction import InteractionEdge, InteractionGraph, InteractionNode
from certicut.optimization.core_root_lp import solve_core_root_lp
from certicut.optimization.exact import brute_force_exact_partition


def _graph(num_qubits: int, weights: list[int]) -> InteractionGraph:
    pairs = [(u, v) for u in range(num_qubits) for v in range(u + 1, num_qubits)]
    edges = tuple(
        InteractionEdge(u, v, 1, {"w": 1}, (), (), 0, 0, float(weight), ())
        for (u, v), weight in zip(pairs, weights)
    )
    nodes = tuple(InteractionNode(qubit, num_qubits - 1, 0.0, num_qubits - 1, 0, 0) for qubit in range(num_qubits))
    return InteractionGraph(num_qubits, nodes, edges)


def main() -> None:
    generator = random.Random(20260812)
    num_qubits = 4
    pair_count = num_qubits * (num_qubits - 1) // 2
    for weights in product(range(4), repeat=pair_count):
        graph = _graph(num_qubits, list(weights))
        values = {
            variant: solve_core_root_lp(graph, variant=variant).lower_bound
            for variant in ("b0", "cardinality", "b2s")
        }
        if abs(values["b0"] - values["cardinality"]) < 1e-8 and values["b2s"] > values["b0"] + 1e-8:
            exact = brute_force_exact_partition(graph, num_fragments=2, qmax=2, exact_num_fragments=True)
            print({"n": num_qubits, "weights": weights, "values": values, "integral_optimum": exact.objective_log_cost, "partition": exact.partition})
            return
    for num_qubits in (6,):
        pair_count = num_qubits * (num_qubits - 1) // 2
        for iteration in range(20_000):
            weights = [generator.randint(0, 9) for _ in range(pair_count)]
            graph = _graph(num_qubits, weights)
            values = {
                variant: solve_core_root_lp(graph, variant=variant).lower_bound
                for variant in ("b0", "cardinality", "triangles", "b2s")
            }
            if (
                abs(values["b0"] - values["cardinality"]) < 1e-8
                and abs(values["b0"] - values["triangles"]) < 1e-8
                and values["b2s"] > values["b0"] + 1e-8
            ):
                exact = brute_force_exact_partition(graph, num_fragments=2, qmax=num_qubits // 2, exact_num_fragments=True)
                print({"n": num_qubits, "iteration": iteration, "weights": weights, "values": values, "integral_optimum": exact.objective_log_cost, "partition": exact.partition})
                return
    raise RuntimeError("no witness found")


if __name__ == "__main__":
    main()
