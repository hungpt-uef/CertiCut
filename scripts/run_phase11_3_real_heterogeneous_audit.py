"""Run E6 on algorithm-derived MQT Bench circuits without basis transpilation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

from mqt.bench.benchmarks.draper_qft_adder import create_circuit as make_draper
from mqt.bench.benchmarks.hhl import create_circuit as make_hhl
from mqt.bench.benchmarks.qft import create_circuit as make_qft
from mqt.bench.benchmarks.qftentangled import create_circuit as make_qftentangled
from mqt.bench.benchmarks.qpeexact import create_circuit as make_qpeexact
from mqt.bench.benchmarks.qpeinexact import create_circuit as make_qpeinexact
from qiskit import qasm3
from qiskit_addon_cutting.qpd import QPDBasis


FAMILIES = (
    "draper_qft_adder",
    "hhl",
    "qpeexact",
    "qpeinexact",
    "qft",
    "qftentangled",
)
SIZES = (6, 8, 10, 12, 14, 16)
FACTORIES = {
    "draper_qft_adder": lambda n: make_draper(n, kind="fixed"),
    "hhl": make_hhl,
    "qpeexact": make_qpeexact,
    "qpeinexact": make_qpeinexact,
    "qft": make_qft,
    "qftentangled": make_qftentangled,
}
IGNORE_OPS = frozenset(("measure", "barrier", "delay"))
QPD_ZERO_TOL = 1e-12
OBJ_TOL = 1e-10
REPRESENTATION_POLICY = "algorithm_semantic_2q_preserving"
OUTPUT = Path("results/phase11_3_algorithm_heterogeneous_audit.json")
MANIFEST = Path("results/phase11_3_algorithm_heterogeneous_manifest.json")


def expose_semantic_two_qubit_ops(qc, max_rounds: int = 20):
    """Decompose only composite operations acting on more than two qubits."""
    out = qc.copy()
    for _ in range(max_rounds):
        names = sorted(
            {
                item.operation.name
                for item in out.data
                if item.operation.name not in IGNORE_OPS and item.operation.num_qubits > 2
            }
        )
        if not names:
            return out
        before_signature = [(item.operation.name, item.operation.num_qubits) for item in out.data]
        out = out.decompose(gates_to_decompose=names, reps=1)
        after_signature = [(item.operation.name, item.operation.num_qubits) for item in out.data]
        if after_signature == before_signature:
            raise RuntimeError(f"Cannot further decompose >2q instructions: {names}")
    raise RuntimeError("Exceeded selective decomposition round limit")


def normalize_param(param):
    try:
        return round(float(param), 12)
    except (TypeError, ValueError):
        return str(param)


def gate_signature(op) -> dict[str, object]:
    return {"name": op.name, "params": tuple(normalize_param(param) for param in op.params)}


def extract_qpd_gate_records(qc):
    """Return numeric 2q QPD records; retain unsupported instructions as evidence."""
    if qc.parameters:
        raise ValueError(f"Unbound circuit parameters remain: {sorted(map(str, qc.parameters))}")
    records = []
    unsupported = []
    for instruction_index, item in enumerate(qc.data):
        op = item.operation
        if op.name in IGNORE_OPS or op.num_qubits == 1:
            continue
        if op.num_qubits != 2:
            unsupported.append(
                {
                    "instruction_index": instruction_index,
                    "name": op.name,
                    "num_qubits": op.num_qubits,
                    "reason": "non_1q_2q_after_selective_decomposition",
                }
            )
            continue
        try:
            rho = float(QPDBasis.from_instruction(op).overhead)
        except Exception as exc:  # Artifact records exact Qiskit rejection.
            unsupported.append(
                {
                    "instruction_index": instruction_index,
                    "name": op.name,
                    "num_qubits": 2,
                    "reason": f"qpd_unavailable: {type(exc).__name__}: {exc}",
                }
            )
            continue
        if not math.isfinite(rho) or rho < 1.0:
            unsupported.append(
                {
                    "instruction_index": instruction_index,
                    "name": op.name,
                    "num_qubits": 2,
                    "reason": f"invalid_qpd_overhead: {rho}",
                }
            )
            continue
        q0 = qc.find_bit(item.qubits[0]).index
        q1 = qc.find_bit(item.qubits[1]).index
        records.append(
            {
                "instruction_index": instruction_index,
                "q0": q0,
                "q1": q1,
                "pair": tuple(sorted((q0, q1))),
                "gate": gate_signature(op),
                "rho": rho,
                "log_rho": math.log(rho),
            }
        )
    return records, unsupported


def gate_histogram(records) -> list[dict[str, object]]:
    histogram = Counter(
        (record["gate"]["name"], record["gate"]["params"], round(record["rho"], 12))
        for record in records
    )
    return [
        {"name": name, "params": list(params), "rho": rho, "count": count}
        for (name, params, rho), count in sorted(histogram.items(), key=lambda item: str(item[0]))
    ]


def aggregate_pair_weights(records):
    count_weight = defaultdict(int)
    qpd_weight = defaultdict(float)
    for record in records:
        if record["rho"] <= 1.0 + QPD_ZERO_TOL:
            continue
        pair = record["pair"]
        count_weight[pair] += 1
        qpd_weight[pair] += record["log_rho"]
    return [(u, v, count_weight[(u, v)], qpd_weight[(u, v)]) for u, v in sorted(count_weight)]


def balanced_partitions(num_qubits: int):
    assert num_qubits % 2 == 0
    for chosen in combinations(range(1, num_qubits), num_qubits // 2 - 1):
        side_a = frozenset((0, *chosen))
        yield tuple(0 if qubit in side_a else 1 for qubit in range(num_qubits))


def evaluate_partition(labels, pair_weights) -> tuple[int, float]:
    cut_count = 0
    qpd_log_cost = 0.0
    for u, v, count_weight, qpd_weight in pair_weights:
        if labels[u] != labels[v]:
            cut_count += count_weight
            qpd_log_cost += qpd_weight
    return cut_count, qpd_log_cost


def evaluate_gate_records(labels, records) -> tuple[int, float]:
    """Direct occurrence-level objective, independent from pair aggregation."""
    cut_records = [
        record
        for record in records
        if record["rho"] > 1.0 + QPD_ZERO_TOL and labels[record["q0"]] != labels[record["q1"]]
    ]
    return len(cut_records), sum(record["log_rho"] for record in cut_records)


def solve_exact_balanced(num_qubits: int, pair_weights) -> dict[str, object]:
    best_count = None
    best_qpd_among_count = math.inf
    best_count_partition = None
    best_qpd = math.inf
    min_count_among_qpd = None
    best_qpd_partition = None
    partitions_enumerated = 0
    for labels in balanced_partitions(num_qubits):
        partitions_enumerated += 1
        cut_count, qpd_log_cost = evaluate_partition(labels, pair_weights)
        if best_count is None or cut_count < best_count:
            best_count, best_qpd_among_count, best_count_partition = cut_count, qpd_log_cost, labels
        elif cut_count == best_count and (qpd_log_cost < best_qpd_among_count - OBJ_TOL or (abs(qpd_log_cost - best_qpd_among_count) <= OBJ_TOL and labels < best_count_partition)):
            best_qpd_among_count, best_count_partition = qpd_log_cost, labels
        if qpd_log_cost < best_qpd - OBJ_TOL:
            best_qpd, min_count_among_qpd, best_qpd_partition = qpd_log_cost, cut_count, labels
        elif abs(qpd_log_cost - best_qpd) <= OBJ_TOL and (cut_count < min_count_among_qpd or (cut_count == min_count_among_qpd and labels < best_qpd_partition)):
            min_count_among_qpd, best_qpd_partition = cut_count, labels
    regret_log = best_qpd_among_count - best_qpd
    return {
        "partitions_enumerated": partitions_enumerated,
        "count_optimum": best_count,
        "J_best_among_count_optima": best_qpd_among_count,
        "count_optimal_partition": list(best_count_partition),
        "J_qpd_optimum": best_qpd,
        "min_count_among_qpd_optima": min_count_among_qpd,
        "qpd_optimal_partition": list(best_qpd_partition),
        "strict_reversal": regret_log > OBJ_TOL,
        "regret_log": regret_log,
        "regret_factor": math.exp(regret_log) if regret_log < 700.0 else math.inf,
        "extra_cuts_required": min_count_among_qpd - best_count,
    }


def cut_gate_histogram(labels, records) -> tuple[Counter, dict[tuple[object, ...], float]]:
    histogram = Counter()
    overheads = {}
    for record in records:
        if labels[record["q0"]] == labels[record["q1"]]:
            continue
        key = (record["gate"]["name"], record["gate"]["params"], round(record["rho"], 12))
        histogram[key] += 1
        overheads[key] = record["rho"]
    return histogram, overheads


def gate_tradeoff(result, records) -> list[dict[str, object]]:
    count_hist, count_overheads = cut_gate_histogram(result["count_optimal_partition"], records)
    qpd_hist, qpd_overheads = cut_gate_histogram(result["qpd_optimal_partition"], records)
    rows = []
    for key in sorted(set(count_hist) | set(qpd_hist), key=str):
        name, params, _ = key
        rho = count_overheads[key] if key in count_overheads else qpd_overheads[key]
        delta_count = qpd_hist[key] - count_hist[key]
        rows.append(
            {
                "gate": name,
                "params": list(params),
                "rho": rho,
                "count_opt_cut": count_hist[key],
                "qpd_opt_cut": qpd_hist[key],
                "delta_qpd_minus_count": delta_count,
                "delta_log_cost": delta_count * math.log(rho),
            }
        )
    expected_count_delta = result["extra_cuts_required"]
    expected_log_delta = result["J_qpd_optimum"] - result["J_best_among_count_optima"]
    actual_count_delta = sum(row["delta_qpd_minus_count"] for row in rows)
    actual_log_delta = sum(row["delta_log_cost"] for row in rows)
    if actual_count_delta != expected_count_delta or abs(actual_log_delta - expected_log_delta) > OBJ_TOL:
        raise AssertionError("gate-class tradeoff does not reproduce exact objective delta")
    return rows


def validate_gate_level_objectives(result, records, pair_weights) -> dict[str, float | int]:
    """Assert direct gate lists agree with independently aggregated edge weights."""
    count_labels = result["count_optimal_partition"]
    qpd_labels = result["qpd_optimal_partition"]
    count_direct, count_direct_j = evaluate_gate_records(count_labels, records)
    qpd_direct, qpd_direct_j = evaluate_gate_records(qpd_labels, records)
    count_aggregate, count_aggregate_j = evaluate_partition(count_labels, pair_weights)
    qpd_aggregate, qpd_aggregate_j = evaluate_partition(qpd_labels, pair_weights)
    checks = (
        count_direct == count_aggregate == result["count_optimum"],
        qpd_direct == qpd_aggregate == result["min_count_among_qpd_optima"],
        abs(count_direct_j - count_aggregate_j) <= OBJ_TOL,
        abs(qpd_direct_j - qpd_aggregate_j) <= OBJ_TOL,
        abs(count_direct_j - result["J_best_among_count_optima"]) <= OBJ_TOL,
        abs(qpd_direct_j - result["J_qpd_optimum"]) <= OBJ_TOL,
    )
    if not all(checks):
        raise AssertionError("gate-level and aggregated objectives disagree")
    return {
        "count_opt_gate_level_cuts": count_direct,
        "count_opt_gate_level_J": count_direct_j,
        "qpd_opt_gate_level_cuts": qpd_direct,
        "qpd_opt_gate_level_J": qpd_direct_j,
        "tolerance": OBJ_TOL,
    }


def audit_record(family: str, num_qubits: int, screen_only: bool) -> dict[str, object]:
    raw = FACTORIES[family](num_qubits)
    qc = expose_semantic_two_qubit_ops(raw)
    records, unsupported = extract_qpd_gate_records(qc)
    positive_log_costs = sorted({round(record["log_rho"], 12) for record in records if record["rho"] > 1.0 + QPD_ZERO_TOL})
    zero_cost = [record for record in records if record["rho"] <= 1.0 + QPD_ZERO_TOL]
    eligible = not unsupported and not zero_cost and len(positive_log_costs) >= 2
    item = {
        "family": family,
        "n": num_qubits,
        "source": "MQT Bench 2.2.2",
        "representation_policy": REPRESENTATION_POLICY,
        "circuit_fingerprint_sha256": hashlib.sha256(qasm3.dumps(qc).encode("utf-8")).hexdigest(),
        "num_operations": len(qc.data),
        "num_two_qubit_ops": len(records),
        "gate_histogram": gate_histogram(records),
        "num_distinct_positive_qpd_costs": len(positive_log_costs),
        "positive_log_costs": positive_log_costs,
        "zero_cost_two_qubit_ops": len(zero_cost),
        "unsupported": unsupported,
        "eligible": eligible,
    }
    if eligible and not screen_only:
        pair_weights = aggregate_pair_weights(records)
        result = solve_exact_balanced(num_qubits, pair_weights)
        item.update(result)
        item["gate_level_consistency"] = validate_gate_level_objectives(result, records, pair_weights)
        item["gate_tradeoff"] = gate_tradeoff(result, records) if result["strict_reversal"] else []
    return item


def decision(records) -> str:
    eligible = [record for record in records if record.get("eligible")]
    strict = [record for record in eligible if record.get("strict_reversal")]
    families = {record["family"] for record in eligible}
    if len(families) >= 2 and len(strict) >= 3:
        return "E6_FULL_RELEVANCE_PASS"
    if strict:
        return "E6_CASE_STUDY_PASS"
    if eligible:
        return "E6_NEGATIVE_PASS"
    return "E6_INELIGIBLE"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen-only", action="store_true")
    args = parser.parse_args()
    records = []
    for family in FAMILIES:
        for num_qubits in SIZES:
            try:
                item = audit_record(family, num_qubits, args.screen_only)
            except Exception as exc:
                item = {
                    "family": family,
                    "n": num_qubits,
                    "source": "MQT Bench 2.2.2",
                    "representation_policy": REPRESENTATION_POLICY,
                    "generation_error": f"{type(exc).__name__}: {exc}",
                    "eligible": False,
                }
            records.append(item)
            print(f"{family} n={num_qubits} 2q={item.get('num_two_qubit_ops', 0)} costs={item.get('num_distinct_positive_qpd_costs', 0)} zero={item.get('zero_cost_two_qubit_ops', 0)} eligible={item['eligible']} reversal={item.get('strict_reversal', False)}")
    artifact = {
        "experiment": "E6_algorithm_derived_heterogeneous_qpd_audit",
        "screen_only": args.screen_only,
        "families": list(FAMILIES),
        "sizes": list(SIZES),
        "source": "MQT Bench 2.2.2",
        "representation_policy": REPRESENTATION_POLICY,
        "eligibility_rule": "no unsupported 2q AND no unit-overhead 2q AND at least two distinct positive QPD costs",
        "reversal_definition": "min_{P: count(P)=count*} J(P) - min_P J(P) > 1e-10",
        "decision": decision(records) if not args.screen_only else "SCREENING_ONLY",
        "records": records,
    }
    OUTPUT.write_text(json.dumps(artifact, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {
        "experiment": artifact["experiment"],
        "artifact": str(OUTPUT).replace("\\", "/"),
        "artifact_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "versions": {
            "qiskit": importlib.metadata.version("qiskit"),
            "mqt_bench": importlib.metadata.version("mqt.bench"),
            "qiskit_addon_cutting": importlib.metadata.version("qiskit-addon-cutting"),
        },
        "representation_policy": REPRESENTATION_POLICY,
        "decision": artifact["decision"],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
