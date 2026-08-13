"""Phase 3C: B2 root diagnostics, B2S equivalence, stress boundary, witnesses."""

from __future__ import annotations

import json
from math import ceil, isclose
from pathlib import Path
import random
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qiskit import QuantumCircuit

from certicut.circuits.benchmarks import make_benchmark_circuit
from certicut.graph.interaction import build_interaction_graph
from certicut.optimization.bnb import solve_certified_bnb
from certicut.optimization.exact import solve_exact_partition
from certicut.optimization.lp import solve_b2_separated_lp, solve_lp_variant


FAMILIES = ("random", "nearest_neighbor", "qaoa_ring", "dense", "community")


def main() -> None:
    output = Path("results")
    root_records = _root_diagnostics()
    _write_jsonl(output / "phase3c_root_records.jsonl", root_records)
    stress_records = _stress_boundary()
    _write_jsonl(output / "phase3c_stress_records.jsonl", stress_records)
    witness = _search_gap_witness()
    (output / "b2_gap_witness.json").write_text(json.dumps(witness, indent=2) + "\n", encoding="utf-8")
    summary = _summary(root_records, stress_records, witness)
    (output / "phase3c_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


def _root_diagnostics() -> list[dict[str, object]]:
    records = []
    for n in (8, 10, 12, 14, 16, 20, 24):
        for family_index, family in enumerate(FAMILIES):
            for seed in range(5):
                graph = build_interaction_graph(make_benchmark_circuit(family, n, 1000 * family_index + seed))
                qmax = ceil(n / 2)
                b2 = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=True, variant="b2_metric")
                b2s = solve_b2_separated_lp(graph, qmax=qmax, exact_num_fragments=True)
                solved = solve_certified_bnb(graph, qmax=qmax, exact_num_fragments=True, lp_variant="b2_metric")
                assert solved.certificate is not None and b2.lower_bound_log is not None
                assert isclose(b2.lower_bound_log, b2s.relaxation.lower_bound_log or 0, abs_tol=1e-9)
                fractional = b2.fractional_variable_count
                records.append({
                    "family": family, "seed": seed, "num_qubits": n, "qmax": qmax,
                    "root_lb": b2.lower_bound_log,
                    "optimum": solved.certificate.upper_bound_log,
                    "root_bound_exact": isclose(b2.lower_bound_log, solved.certificate.upper_bound_log, abs_tol=1e-9),
                    "root_lp_integral": fractional == 0,
                    "root_fractional_variable_count": fractional,
                    "root_max_fractionality": b2.max_fractionality,
                    "root_integrality_gap_log": solved.certificate.upper_bound_log - b2.lower_bound_log,
                    "b2_constraints": b2.constraint_count,
                    "b2s_constraints": b2s.relaxation.constraint_count,
                    "b2s_rounds": b2s.separation_rounds,
                    "b2s_triangles_added": b2s.triangles_added,
                    "b2s_lp_solves": b2s.lp_solve_count,
                    "b2s_lp_time_s": b2s.lp_time_total_s,
                    "b2s_build_time_s": b2s.matrix_build_time_s,
                })
    return records


def _stress_boundary() -> list[dict[str, object]]:
    records = []
    regimes = ("random_p10", "random_p50", "community_noise", "weighted_random")
    for n in (26, 32, 40):
        for regime_index, regime in enumerate(regimes):
            for seed in range(2):
                circuit = _stress_circuit(regime, n, 10000 * regime_index + seed)
                graph = build_interaction_graph(circuit)
                qmax = ceil(n / 2)
                b2s = solve_b2_separated_lp(graph, qmax=qmax, exact_num_fragments=True, policy="top_k", top_k=500)
                records.append({
                    "regime": regime, "seed": seed, "num_qubits": n, "num_edges": len(graph.edges),
                    "root_lb": b2s.relaxation.lower_bound_log,
                    "root_lp_integral": b2s.relaxation.fractional_variable_count == 0,
                    "root_fractional_variable_count": b2s.relaxation.fractional_variable_count,
                    "root_max_fractionality": b2s.relaxation.max_fractionality,
                    "separation_rounds": b2s.separation_rounds,
                    "triangles_added": b2s.triangles_added,
                    "lp_solve_count": b2s.lp_solve_count,
                    "lp_time_s": b2s.lp_time_total_s,
                    "matrix_build_time_s": b2s.matrix_build_time_s,
                    "constraints": b2s.relaxation.constraint_count,
                })
    return records


def _stress_circuit(regime: str, n: int, seed: int) -> QuantumCircuit:
    generator = random.Random(seed)
    circuit = QuantumCircuit(n)
    if regime.startswith("random_p"):
        probability = float(regime[-2:]) / 100
        for u in range(n):
            for v in range(u + 1, n):
                if generator.random() < probability:
                    circuit.cx(u, v)
    elif regime == "community_noise":
        split = n // 2
        for u in range(n):
            for v in range(u + 1, n):
                same = (u < split) == (v < split)
                if generator.random() < (0.45 if same else 0.18):
                    circuit.cx(u, v)
    elif regime == "weighted_random":
        for u in range(n):
            for v in range(u + 1, n):
                if generator.random() < 0.22:
                    for _ in range(generator.randint(1, 5)):
                        circuit.cx(u, v)
    return circuit


def _search_gap_witness() -> dict[str, object]:
    generator = random.Random(20260810)
    for n in (8, 10, 12):
        for trial in range(150):
            circuit = QuantumCircuit(n)
            probability = generator.choice((0.1, 0.25, 0.5, 0.75))
            for u in range(n):
                for v in range(u + 1, n):
                    if generator.random() < probability:
                        for _ in range(generator.randint(1, 5)):
                            circuit.cx(u, v)
            graph = build_interaction_graph(circuit)
            qmax = ceil(n / 2)
            exact = solve_exact_partition(graph, num_fragments=2, qmax=qmax, exact_num_fragments=True)
            b2 = solve_lp_variant(graph, qmax=qmax, exact_num_fragments=True, variant="b2_metric")
            gap = (exact.objective_log_cost or 0) - (b2.lower_bound_log or 0)
            if gap > 1e-8:
                return {
                    "found": True, "num_qubits": n, "trial": trial, "density": probability,
                    "objective_optimum_log": exact.objective_log_cost, "b2_root_lb_log": b2.lower_bound_log,
                    "integrality_gap_log": gap, "root_fractional_variable_count": b2.fractional_variable_count,
                    "root_max_fractionality": b2.max_fractionality,
                    "instructions": [[edge.u, edge.v, edge.gate_count] for edge in graph.edges],
                }
    return {"found": False, "trials_per_size": 150, "sizes": [8, 10, 12]}


def _summary(root: list[dict[str, object]], stress: list[dict[str, object]], witness: dict[str, object]) -> dict[str, object]:
    return {
        "root_corpus": {
            "instances": len(root),
            "root_bound_exact": sum(bool(r["root_bound_exact"]) for r in root),
            "root_lp_integral": sum(bool(r["root_lp_integral"]) for r in root),
            "b2s_matches_b2": len(root),
            "median_b2s_triangles_added": statistics.median(int(r["b2s_triangles_added"]) for r in root),
            "median_b2s_rounds": statistics.median(int(r["b2s_rounds"]) for r in root),
            "by_family": {
                family: {
                    "root_bound_exact": sum(bool(r["root_bound_exact"]) for r in subset),
                    "root_lp_integral": sum(bool(r["root_lp_integral"]) for r in subset),
                    "instances": len(subset),
                }
                for family in FAMILIES
                if (subset := [r for r in root if r["family"] == family])
            },
        },
        "stress_root_only": {
            "instances": len(stress),
            "integral_roots": sum(bool(r["root_lp_integral"]) for r in stress),
            "fractional_roots": sum(not bool(r["root_lp_integral"]) for r in stress),
            "median_triangles_added": statistics.median(int(r["triangles_added"]) for r in stress),
            "median_lp_time_s": statistics.median(float(r["lp_time_s"]) for r in stress),
            "max_constraints": max(int(r["constraints"]) for r in stress),
        },
        "gap_witness": witness,
    }


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


if __name__ == "__main__":
    main()
