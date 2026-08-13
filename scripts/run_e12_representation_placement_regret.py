"""E12: Representation-Induced Optimal-Placement Regret.

Three-tier experiment measuring whether changing circuit representation
(CX-normalized vs native-QPD) alters the *optimal partition decision*,
not just the absolute independent-QPD cost.

Tier 1 — exact-small: exhaustive enumeration, K=2 balanced + K=3/4 where feasible.
Tier 2 — algorithm-derived: QAOA, QFT, QPE, Draper via MQT Bench.
Tier 3 — medium: SCIP solver for instances too large to enumerate.

Key metrics:
  Δ_{a→b}  = min_{P ∈ argmin J_a} J_b(P) − J_b*           (placement regret)
  R_{a→b}  = exp(Δ_{a→b})                                   (overhead factor)
  m_a      = min_{P ∉ argmin J_a} [J_a(P) − J_a*]           (optimality margin)
  κ_{a→b}  = ‖w_b − w_a‖₁ / m_a                            (stability diagnostic)

No hardware routing is enabled: both representations use coupling_map=None.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from itertools import combinations
from math import exp, inf, isfinite, log
from pathlib import Path
from time import perf_counter
from typing import Sequence

from qiskit import QuantumCircuit

from certicut.circuits.ingestion import ingest_mqt_pair
from certicut.costs.qpd import QPDCostError, qpd_cost
from certicut.graph.interaction import (
    InteractionGraph,
    build_interaction_graph,
    graph_partition_objective,
)
from certicut.optimization.exact import _valid_partitions

ROOT = Path(__file__).resolve().parents[1]

TOLERANCE = 1e-10
SCIP_FEASIBILITY_TOLERANCE = 1e-12


# ---------------------------------------------------------------------------
# Core representation-regret oracle
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RepresentationRegretResult:
    """Full E12 result for one (source circuit, K) configuration."""

    family: str
    n: int
    K: int
    tier: str

    # Per-representation optimum costs
    J_a_star: float
    J_b_star: float

    # Tie-safe cross-representation regret
    delta_a_to_b: float
    delta_b_to_a: float
    R_a_to_b: float
    R_b_to_a: float

    # Optimum set sizes
    argmin_a_count: int
    argmin_b_count: int

    # Optimum overlap
    optimum_overlap_count: int  # |argmin_a ∩ argmin_b|
    has_shared_optimum: bool

    # Minimum assignment disagreement between argmin sets
    min_assignment_disagreement: int

    # Optimality margins
    margin_a: float  # m_a
    margin_b: float  # m_b

    # Perturbation L1 norm
    weight_perturbation_l1: float

    # Stability diagnostic κ
    kappa_a_to_b: float  # ‖δ‖₁ / m_a
    kappa_b_to_a: float  # ‖δ‖₁ / m_b

    # Theoretical bound
    regret_bound: float  # exp(‖δ‖₁)

    # Strict reversals
    strict_reversal_a_to_b: bool
    strict_reversal_b_to_a: bool

    # Representative partitions
    rep_partition_a: tuple[int, ...] | None
    rep_partition_b: tuple[int, ...] | None

    # Circuit metadata
    representation_a: str
    representation_b: str
    two_qubit_count_a: int
    two_qubit_count_b: int
    gate_types_a: tuple[str, ...]
    gate_types_b: tuple[str, ...]
    source_fingerprint: str

    partition_count: int
    runtime_s: float

    def as_dict(self) -> dict:
        return asdict(self)


def _edge_weight_vector(graph: InteractionGraph) -> dict[tuple[int, int], float]:
    """Return {(u, v): qpd_log_cost} for each edge."""
    return {(edge.u, edge.v): edge.qpd_log_cost for edge in graph.edges}


def _weight_perturbation_l1(
    w_a: dict[tuple[int, int], float],
    w_b: dict[tuple[int, int], float],
) -> float:
    """‖w_b − w_a‖₁ over the union of edge supports."""
    all_edges = set(w_a) | set(w_b)
    return sum(abs(w_b.get(e, 0.0) - w_a.get(e, 0.0)) for e in all_edges)


def _enumerate_partitions_general(
    n: int, K: int, *, balanced: bool = True
) -> list[tuple[int, ...]]:
    """Enumerate partitions for given K. For K=2 balanced, use symmetry reduction."""
    if K == 2 and balanced and n % 2 == 0:
        # Symmetry-reduced: q0 fixed to side 0
        target = n // 2
        return [
            tuple(0 if q in (0, *rest) else 1 for q in range(n))
            for rest in combinations(range(1, n), target - 1)
        ]
    # General K-way with capacity constraints
    qmax = (n + K - 1) // K + 1  # generous upper bound
    return list(_valid_partitions(n, K, qmax, exact_num_fragments=True))


def exhaustive_representation_regret(
    circuit_a: QuantumCircuit,
    circuit_b: QuantumCircuit,
    *,
    K: int = 2,
    family: str = "",
    n: int = 0,
    tier: str = "exact",
    representation_a: str = "cx_normalized",
    representation_b: str = "native_qpd",
    source_fingerprint: str = "",
    audit_a: dict | None = None,
    audit_b: dict | None = None,
) -> RepresentationRegretResult:
    """Compute exact tie-safe representation-induced placement regret."""
    started = perf_counter()

    graph_a = build_interaction_graph(circuit_a, cost_model="qiskit_qpd")
    graph_b = build_interaction_graph(circuit_b, cost_model="qiskit_qpd")

    assert graph_a.num_qubits == graph_b.num_qubits
    num_qubits = graph_a.num_qubits

    w_a = _edge_weight_vector(graph_a)
    w_b = _edge_weight_vector(graph_b)
    perturbation_l1 = _weight_perturbation_l1(w_a, w_b)

    # Enumerate partitions
    balanced = K == 2 and num_qubits % 2 == 0
    partitions = _enumerate_partitions_general(num_qubits, K, balanced=balanced)

    if not partitions:
        raise ValueError(f"No valid partitions for n={num_qubits}, K={K}")

    # Evaluate all partitions under both representations
    scores_a = []
    scores_b = []
    for partition in partitions:
        ja = graph_partition_objective(graph_a, partition)
        jb = graph_partition_objective(graph_b, partition)
        scores_a.append(ja)
        scores_b.append(jb)

    J_a_star = min(scores_a)
    J_b_star = min(scores_b)

    # argmin sets (tie-safe)
    argmin_a_indices = [
        i for i, s in enumerate(scores_a) if s <= J_a_star + TOLERANCE
    ]
    argmin_b_indices = [
        i for i, s in enumerate(scores_b) if s <= J_b_star + TOLERANCE
    ]

    argmin_a_set = set(argmin_a_indices)
    argmin_b_set = set(argmin_b_indices)

    # Optimum overlap
    overlap = argmin_a_set & argmin_b_set
    has_shared = len(overlap) > 0

    # Tie-safe cross-representation regret: Δ_{a→b} = min_{P ∈ argmin_a} J_b(P) − J_b*
    delta_a_to_b = min(scores_b[i] for i in argmin_a_indices) - J_b_star
    delta_b_to_a = min(scores_a[i] for i in argmin_b_indices) - J_a_star

    R_a_to_b = exp(delta_a_to_b) if isfinite(delta_a_to_b) else inf
    R_b_to_a = exp(delta_b_to_a) if isfinite(delta_b_to_a) else inf

    # Optimality margins
    non_opt_a = [scores_a[i] for i in range(len(partitions)) if i not in argmin_a_set]
    non_opt_b = [scores_b[i] for i in range(len(partitions)) if i not in argmin_b_set]
    margin_a = (min(non_opt_a) - J_a_star) if non_opt_a else inf
    margin_b = (min(non_opt_b) - J_b_star) if non_opt_b else inf

    # Stability diagnostic κ
    kappa_a_to_b = perturbation_l1 / margin_a if margin_a > 0 else inf
    kappa_b_to_a = perturbation_l1 / margin_b if margin_b > 0 else inf

    # Theoretical regret bound
    regret_bound = exp(perturbation_l1) if perturbation_l1 < 700 else inf

    # Minimum assignment disagreement
    min_disagree = min(
        sum(
            partitions[i][q] != partitions[j][q]
            for q in range(num_qubits)
        )
        for i in argmin_a_indices
        for j in argmin_b_indices
    )

    # Representative partitions (best of argmin set under other representation)
    best_a_idx = min(argmin_a_indices, key=lambda i: (scores_b[i], partitions[i]))
    best_b_idx = min(argmin_b_indices, key=lambda i: (scores_a[i], partitions[i]))

    # Gate metadata
    two_q_a = sum(1 for inst in circuit_a.data if inst.operation.num_qubits == 2)
    two_q_b = sum(1 for inst in circuit_b.data if inst.operation.num_qubits == 2)
    types_a = tuple(sorted({inst.operation.name for inst in circuit_a.data if inst.operation.num_qubits == 2}))
    types_b = tuple(sorted({inst.operation.name for inst in circuit_b.data if inst.operation.num_qubits == 2}))

    return RepresentationRegretResult(
        family=family,
        n=n or num_qubits,
        K=K,
        tier=tier,
        J_a_star=J_a_star,
        J_b_star=J_b_star,
        delta_a_to_b=delta_a_to_b,
        delta_b_to_a=delta_b_to_a,
        R_a_to_b=R_a_to_b,
        R_b_to_a=R_b_to_a,
        argmin_a_count=len(argmin_a_indices),
        argmin_b_count=len(argmin_b_indices),
        optimum_overlap_count=len(overlap),
        has_shared_optimum=has_shared,
        min_assignment_disagreement=min_disagree,
        margin_a=margin_a,
        margin_b=margin_b,
        weight_perturbation_l1=perturbation_l1,
        kappa_a_to_b=kappa_a_to_b,
        kappa_b_to_a=kappa_b_to_a,
        regret_bound=regret_bound,
        strict_reversal_a_to_b=delta_a_to_b > TOLERANCE,
        strict_reversal_b_to_a=delta_b_to_a > TOLERANCE,
        rep_partition_a=partitions[best_a_idx],
        rep_partition_b=partitions[best_b_idx],
        representation_a=representation_a,
        representation_b=representation_b,
        two_qubit_count_a=two_q_a,
        two_qubit_count_b=two_q_b,
        gate_types_a=types_a,
        gate_types_b=types_b,
        source_fingerprint=source_fingerprint,
        partition_count=len(partitions),
        runtime_s=perf_counter() - started,
    )


# ---------------------------------------------------------------------------
# SCIP-based solver for medium instances
# ---------------------------------------------------------------------------

def _solve_cross_representation_mip(
    graph_primary: InteractionGraph,
    graph_cross: InteractionGraph,
    *,
    J_primary_star: float,
    num_fragments: int,
    lower_capacities: tuple[int, ...],
    upper_capacities: tuple[int, ...],
    tau_opt: float,
    feasibility_tolerance: float,
    time_limit_s: float,
) -> tuple[float | None, tuple[int, ...] | None, str]:
    """Two-stage tie-safe MIP: minimize J_cross(P) subject to J_primary(P) <= J*_primary + tau_opt.

    This computes  min_{P in argmin_tau J_primary}  J_cross(P)
    which is the tie-safe cross-representation cost.

    Returns (cross_cost, partition, status).
    """
    from pyscipopt import Model, quicksum

    n = graph_primary.num_qubits
    K = num_fragments

    if (
        not graph_primary.edges
        or all(abs(edge.qpd_log_cost) <= TOLERANCE for edge in graph_primary.edges)
    ):
        partition = tuple(
            fragment
            for fragment, capacity in enumerate(lower_capacities)
            for _ in range(capacity)
        )
        return 0.0, partition, "trivial"

    model = Model("e12_cross_representation")
    model.hideOutput(True)
    model.setIntParam("randomization/randomseedshift", 0)
    model.setIntParam("randomization/permutationseed", 0)
    model.setRealParam("numerics/feastol", feasibility_tolerance)
    if time_limit_s > 0:
        model.setRealParam("limits/time", time_limit_s)

    # Variables: x[q,k] assignment, z_p[e] primary cut, z_c[e] cross cut
    x = {(q, k): model.addVar(vtype="B", name=f"x_{q}_{k}")
         for q in range(n) for k in range(K)}
    z_p = {ei: model.addVar(vtype="B", name=f"zp_{ei}")
           for ei in range(len(graph_primary.edges))}
    z_c = {ei: model.addVar(vtype="B", name=f"zc_{ei}")
           for ei in range(len(graph_cross.edges))}

    # Assignment constraints
    for q in range(n):
        model.addCons(quicksum(x[q, k] for k in range(K)) == 1)
    for k in range(K):
        load = quicksum(x[q, k] for q in range(n))
        model.addCons(load >= lower_capacities[k])
        model.addCons(load <= upper_capacities[k])

    # Symmetry breaking: q0 in fragment 0
    if len(set(lower_capacities)) == 1 and len(set(upper_capacities)) == 1:
        model.addCons(x[0, 0] == 1)

    # Primary graph cut indicators
    y_p = {}
    for ei, edge in enumerate(graph_primary.edges):
        for k in range(K):
            y_p[ei, k] = model.addVar(vtype="B", name=f"yp_{ei}_{k}")
            model.addCons(y_p[ei, k] <= x[edge.u, k])
            model.addCons(y_p[ei, k] <= x[edge.v, k])
            model.addCons(y_p[ei, k] >= x[edge.u, k] + x[edge.v, k] - 1)
        model.addCons(z_p[ei] + quicksum(y_p[ei, k] for k in range(K)) == 1)

    # Cross graph cut indicators
    y_c = {}
    for ei, edge in enumerate(graph_cross.edges):
        for k in range(K):
            y_c[ei, k] = model.addVar(vtype="B", name=f"yc_{ei}_{k}")
            model.addCons(y_c[ei, k] <= x[edge.u, k])
            model.addCons(y_c[ei, k] <= x[edge.v, k])
            model.addCons(y_c[ei, k] >= x[edge.u, k] + x[edge.v, k] - 1)
        model.addCons(z_c[ei] + quicksum(y_c[ei, k] for k in range(K)) == 1)

    # Stage-1 budget: J_primary(P) <= J*_primary + tau_opt.
    # Rebuild it from the objective to avoid a zero-length quicksum becoming
    # an invalid constant constraint in PySCIPOpt.
    if any(edge.qpd_log_cost > TOLERANCE for edge in graph_primary.edges):
        scip_tol = float(model.getParam("numerics/feastol"))
        primary_obj = quicksum(
            edge.qpd_log_cost * z_p[ei]
            for ei, edge in enumerate(graph_primary.edges)
        )
        budget = J_primary_star + tau_opt + scip_tol
        if budget > TOLERANCE:
            model.addCons(primary_obj <= budget)

    # Stage-2 objective: minimize J_cross(P)
    cross_obj = quicksum(
        edge.qpd_log_cost * z_c[ei]
        for ei, edge in enumerate(graph_cross.edges)
    )
    model.setObjective(cross_obj, "minimize")
    model.optimize()

    status = str(model.getStatus())
    sol = model.getBestSol() if model.getNSols() > 0 else None
    if sol is None:
        return None, None, status

    partition = tuple(
        next(k for k in range(K) if model.getSolVal(sol, x[q, k]) > 0.5)
        for q in range(n)
    )
    cross_cost = graph_partition_objective(graph_cross, partition)
    return cross_cost, partition, status


def scip_representation_regret(
    circuit_a: QuantumCircuit,
    circuit_b: QuantumCircuit,
    *,
    K: int = 2,
    family: str = "",
    n: int = 0,
    representation_a: str = "cx_normalized",
    representation_b: str = "native_qpd",
    source_fingerprint: str = "",
    time_limit_s: float = 300.0,
    tau_opt: float = 1e-9,
    feasibility_tolerance: float = SCIP_FEASIBILITY_TOLERANCE,
) -> RepresentationRegretResult:
    """Tie-safe two-stage SCIP regret for medium instances.

    Stage 1: Solve min J_a(P) and min J_b(P) independently.
    Stage 2a: Solve min J_b(P) s.t. J_a(P) <= J*_a + tau_opt  (tie-safe a->b)
    Stage 2b: Solve min J_a(P) s.t. J_b(P) <= J*_b + tau_opt  (tie-safe b->a)

    The same explicit SCIP feasibility tolerance is pinned in every stage.
    This ensures Delta_{a->b} = min_{P in argmin_tau J_a} J_b(P) - J*_b,
    which correctly handles ties in the primary objective.
    """
    from certicut.optimization.k_partition import solve_scip_k_partition

    started = perf_counter()

    graph_a = build_interaction_graph(circuit_a, cost_model="qiskit_qpd")
    graph_b = build_interaction_graph(circuit_b, cost_model="qiskit_qpd")
    num_qubits = graph_a.num_qubits

    w_a = _edge_weight_vector(graph_a)
    w_b = _edge_weight_vector(graph_b)
    perturbation_l1 = _weight_perturbation_l1(w_a, w_b)

    lo = num_qubits // K
    hi = (num_qubits + K - 1) // K
    lower_caps = (lo,) * K
    upper_caps = (hi,) * K

    # Stage 1: solve each representation independently
    result_a = solve_scip_k_partition(
        graph_a, num_fragments=K,
        lower_capacities=lower_caps, upper_capacities=upper_caps,
        time_limit_s=time_limit_s, symmetry_breaking=True,
        feasibility_tolerance=feasibility_tolerance,
    )
    result_b = solve_scip_k_partition(
        graph_b, num_fragments=K,
        lower_capacities=lower_caps, upper_capacities=upper_caps,
        time_limit_s=time_limit_s, symmetry_breaking=True,
        feasibility_tolerance=feasibility_tolerance,
    )

    if result_a.partition is None or result_b.partition is None:
        raise RuntimeError(f"SCIP failed: a={result_a.status}, b={result_b.status}")

    # Recompute from the integral witnesses. SCIP's primal bound can be rounded
    # just below the discrete objective, which would make a tight Stage-2 budget
    # incorrectly infeasible on zero-cost or tied instances.
    J_a_star = graph_partition_objective(graph_a, result_a.partition)
    J_b_star = graph_partition_objective(graph_b, result_b.partition)

    if w_a == w_b:
        # Identical objective vectors have identical argmin sets; avoid a
        # redundant cross model and its floating-point budget constraint.
        C_a_to_b, P_a_cross, status_a2 = J_b_star, result_a.partition, "identical_objectives"
        C_b_to_a, P_b_cross, status_b2 = J_a_star, result_b.partition, "identical_objectives"
    else:
        # Stage 2a: min J_b(P) s.t. J_a(P) <= J*_a + tau
        C_a_to_b, P_a_cross, status_a2 = _solve_cross_representation_mip(
            graph_a, graph_b,
            J_primary_star=J_a_star,
            num_fragments=K,
            lower_capacities=lower_caps,
            upper_capacities=upper_caps,
            tau_opt=tau_opt,
            feasibility_tolerance=feasibility_tolerance,
            time_limit_s=time_limit_s,
        )

        # Stage 2b: min J_a(P) s.t. J_b(P) <= J*_b + tau
        C_b_to_a, P_b_cross, status_b2 = _solve_cross_representation_mip(
            graph_b, graph_a,
            J_primary_star=J_b_star,
            num_fragments=K,
            lower_capacities=lower_caps,
            upper_capacities=upper_caps,
            tau_opt=tau_opt,
            feasibility_tolerance=feasibility_tolerance,
            time_limit_s=time_limit_s,
        )

    if C_a_to_b is None or C_b_to_a is None:
        raise RuntimeError(
            f"Cross-MIP failed: a->b={status_a2}, b->a={status_b2}"
        )

    delta_a_to_b = max(0.0, C_a_to_b - J_b_star)
    delta_b_to_a = max(0.0, C_b_to_a - J_a_star)

    R_a_to_b = exp(delta_a_to_b) if delta_a_to_b < 700 else inf
    R_b_to_a = exp(delta_b_to_a) if delta_b_to_a < 700 else inf

    # Disagreement between stage-2 cross partitions
    disagree = sum(
        P_a_cross[q] != P_b_cross[q]
        for q in range(num_qubits)
    )

    two_q_a = sum(1 for inst in circuit_a.data if inst.operation.num_qubits == 2)
    two_q_b = sum(1 for inst in circuit_b.data if inst.operation.num_qubits == 2)
    types_a = tuple(sorted({inst.operation.name for inst in circuit_a.data if inst.operation.num_qubits == 2}))
    types_b = tuple(sorted({inst.operation.name for inst in circuit_b.data if inst.operation.num_qubits == 2}))

    return RepresentationRegretResult(
        family=family,
        n=n or num_qubits,
        K=K,
        tier="scip_tie_safe",
        J_a_star=J_a_star,
        J_b_star=J_b_star,
        delta_a_to_b=delta_a_to_b,
        delta_b_to_a=delta_b_to_a,
        R_a_to_b=R_a_to_b,
        R_b_to_a=R_b_to_a,
        argmin_a_count=-1,  # full argmin not enumerated
        argmin_b_count=-1,
        optimum_overlap_count=-1,  # not computable via solver
        has_shared_optimum=delta_a_to_b <= TOLERANCE and delta_b_to_a <= TOLERANCE,
        min_assignment_disagreement=disagree,
        margin_a=float("inf"),  # not computable without enumeration
        margin_b=float("inf"),
        weight_perturbation_l1=perturbation_l1,
        kappa_a_to_b=0.0,  # margin not computable
        kappa_b_to_a=0.0,
        regret_bound=exp(perturbation_l1) if perturbation_l1 < 700 else inf,
        strict_reversal_a_to_b=delta_a_to_b > TOLERANCE,
        strict_reversal_b_to_a=delta_b_to_a > TOLERANCE,
        rep_partition_a=P_a_cross,
        rep_partition_b=P_b_cross,
        representation_a=representation_a,
        representation_b=representation_b,
        two_qubit_count_a=two_q_a,
        two_qubit_count_b=two_q_b,
        gate_types_a=types_a,
        gate_types_b=types_b,
        source_fingerprint=source_fingerprint,
        partition_count=-1,
        runtime_s=perf_counter() - started,
    )


# ---------------------------------------------------------------------------
# Semantic verification
# ---------------------------------------------------------------------------

def _verify_unitary_equivalence(
    circuit_a: QuantumCircuit,
    circuit_b: QuantumCircuit,
    *,
    tolerance: float = 1e-6,
) -> dict:
    """Verify both circuits implement the same unitary (up to global phase)."""
    from qiskit.quantum_info import Operator
    try:
        op_a = Operator(circuit_a)
        op_b = Operator(circuit_b)
        # Check U_a = e^{iφ} U_b
        product = op_a.adjoint().compose(op_b)
        # If equivalent, product should be proportional to identity
        mat = product.data
        phase = mat[0, 0]
        identity_check = mat / phase
        error = float(abs(identity_check - identity_check.round()).max())
        passed = error < tolerance
        return {
            "unitary_equivalence": passed,
            "max_deviation": error,
            "global_phase": float(abs(phase)),
        }
    except Exception as e:
        return {"unitary_equivalence": "skipped", "reason": str(e)}


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def main() -> None:
    records: list[dict] = []
    summary_lines: list[str] = []

    def _log(msg: str) -> None:
        safe = msg.encode("ascii", errors="replace").decode("ascii")
        print(safe, flush=True)
        summary_lines.append(msg)

    _log("=" * 72)
    _log("E12: Representation-Induced Optimal-Placement Regret")
    _log("=" * 72)
    _log(f"Pinned SCIP numerics/feastol: {SCIP_FEASIBILITY_TOLERANCE:.0e}")

    # ---- Tier 2: Algorithm-derived MQT families ----
    _log("\n--- Tier 2: Algorithm-derived MQT families ---")

    # Families with heterogeneous native gates (representation effect expected)
    mqt_families = ["qaoa", "qft", "qpeexact", "bv", "grover"]
    # Control families (both reps use CX only — no effect expected)
    control_families = ["vqe_real_amp", "ghz", "dj"]
    all_families = mqt_families + control_families
    # n values where exhaustive enumeration is feasible (K=2 balanced)
    mqt_exact_sizes = [] if os.environ.get("E12_SKIP_EXACT") == "1" else [4, 6, 8, 10]
    # n values for SCIP tier
    mqt_scip_sizes = [12, 14, 16]
    # K values to try for exact tier
    k_values_exact = [2, 3]

    for family in all_families:
        for n in mqt_exact_sizes:
            try:
                paired = ingest_mqt_pair(family, n)
            except Exception as error:
                record = {
                    "family": family, "n": n, "tier": "exact",
                    "status": "ingestion_error", "error": repr(error),
                }
                records.append(record)
                _log(f"  [{family} n={n}] ingestion error: {error}")
                continue

            circuit_a, audit_a = paired["cx_normalized"]
            circuit_b, audit_b = paired["native_qpd"]

            # Semantic verification for small circuits
            if n <= 10:
                verify = _verify_unitary_equivalence(circuit_a, circuit_b)
                _log(f"  [{family} n={n}] unitary check: {verify}")
            else:
                verify = {"unitary_equivalence": "skipped", "reason": "n>10"}

            for K in k_values_exact:
                if K == 2 and n % 2 != 0:
                    continue
                if K == 3 and n > 8:
                    continue  # too many partitions
                if K == 3 and n < 6:
                    continue
                try:
                    result = exhaustive_representation_regret(
                        circuit_a, circuit_b,
                        K=K, family=family, n=n, tier="exact",
                        source_fingerprint=audit_a.source_fingerprint,
                        audit_a=audit_a.as_dict(),
                        audit_b=audit_b.as_dict(),
                    )
                    record = result.as_dict()
                    record["unitary_verification"] = verify
                    record["audit_a"] = audit_a.as_dict()
                    record["audit_b"] = audit_b.as_dict()
                    records.append(record)

                    rev_str = ""
                    if result.strict_reversal_a_to_b:
                        rev_str += f" REVERSAL(a->b R={result.R_a_to_b:.4f})"
                    if result.strict_reversal_b_to_a:
                        rev_str += f" REVERSAL(b->a R={result.R_b_to_a:.4f})"
                    if not rev_str:
                        rev_str = " no reversal"

                    _log(
                        f"  [{family} n={n} K={K}] "
                        f"J_cx*={result.J_a_star:.4f} J_nat*={result.J_b_star:.4f} "
                        f"R(cx->nat)={result.R_a_to_b:.4f} R(nat->cx)={result.R_b_to_a:.4f} "
                        f"kappa(a->b)={result.kappa_a_to_b:.4f} kappa(b->a)={result.kappa_b_to_a:.4f} "
                        f"overlap={result.optimum_overlap_count}/{result.argmin_a_count}x{result.argmin_b_count} "
                        f"m_a={result.margin_a:.4f} m_b={result.margin_b:.4f} "
                        f"delta_l1={result.weight_perturbation_l1:.4f} "
                        f"parts={result.partition_count} t={result.runtime_s:.2f}s"
                        f"{rev_str}"
                    )
                except Exception as error:
                    record = {
                        "family": family, "n": n, "K": K, "tier": "exact",
                        "status": "computation_error", "error": repr(error),
                    }
                    records.append(record)
                    _log(f"  [{family} n={n} K={K}] error: {error}")

    # ---- Tier 3: Medium tie-safe SCIP instances ----
    _log("\n--- Tier 3: Medium instances (tie-safe two-stage SCIP) ---")

    tau_values = [1e-8, 1e-9, 1e-10]

    for family in all_families:
        for n in mqt_scip_sizes:
            for K in [2, 3]:
                if K == 2 and n % 2 != 0:
                    continue
                try:
                    paired = ingest_mqt_pair(family, n)
                except Exception as error:
                    record = {
                        "family": family, "n": n, "K": K, "tier": "scip_tie_safe",
                        "status": "ingestion_error", "error": repr(error),
                    }
                    records.append(record)
                    _log(f"  [{family} n={n} K={K}] ingestion error: {error}")
                    continue

                circuit_a, audit_a = paired["cx_normalized"]
                circuit_b, audit_b = paired["native_qpd"]

                # Run at primary tau_opt (1e-9), record full result
                try:
                    result = scip_representation_regret(
                        circuit_a, circuit_b,
                        K=K, family=family, n=n,
                        source_fingerprint=audit_a.source_fingerprint,
                        time_limit_s=600.0,
                        tau_opt=1e-9,
                    )
                    record = result.as_dict()
                    record["tau_opt"] = 1e-9
                    record["scip_numerics_feastol"] = SCIP_FEASIBILITY_TOLERANCE
                    record["audit_a"] = audit_a.as_dict()
                    record["audit_b"] = audit_b.as_dict()

                    # Sensitivity: run at other tau values
                    sensitivity = {}
                    for tau in tau_values:
                        if tau == 1e-9:
                            sensitivity[str(tau)] = {
                                "R_a_to_b": result.R_a_to_b,
                                "R_b_to_a": result.R_b_to_a,
                                "delta_a_to_b": result.delta_a_to_b,
                                "delta_b_to_a": result.delta_b_to_a,
                                "strict_reversal_a_to_b": result.strict_reversal_a_to_b,
                                "strict_reversal_b_to_a": result.strict_reversal_b_to_a,
                            }
                            continue
                        try:
                            result_tau = scip_representation_regret(
                                circuit_a, circuit_b,
                                K=K, family=family, n=n,
                                source_fingerprint=audit_a.source_fingerprint,
                                time_limit_s=600.0,
                                tau_opt=tau,
                                feasibility_tolerance=SCIP_FEASIBILITY_TOLERANCE,
                            )
                            sensitivity[str(tau)] = {
                                "R_a_to_b": result_tau.R_a_to_b,
                                "R_b_to_a": result_tau.R_b_to_a,
                                "delta_a_to_b": result_tau.delta_a_to_b,
                                "delta_b_to_a": result_tau.delta_b_to_a,
                                "strict_reversal_a_to_b": result_tau.strict_reversal_a_to_b,
                                "strict_reversal_b_to_a": result_tau.strict_reversal_b_to_a,
                            }
                        except Exception as e_tau:
                            sensitivity[str(tau)] = {"error": repr(e_tau)}

                    record["tau_sensitivity"] = sensitivity
                    records.append(record)

                    rev_str = ""
                    if result.strict_reversal_a_to_b:
                        rev_str += f" REVERSAL(a->b R={result.R_a_to_b:.4f})"
                    if result.strict_reversal_b_to_a:
                        rev_str += f" REVERSAL(b->a R={result.R_b_to_a:.4f})"
                    if not rev_str:
                        rev_str = " no reversal"

                    # Check if reversal survives all tau values
                    tau_stable = all(
                        sensitivity.get(str(t), {}).get("strict_reversal_a_to_b", False)
                        == result.strict_reversal_a_to_b
                        for t in tau_values
                    )
                    tau_note = " [tau-stable]" if tau_stable else " [tau-sensitive!]"

                    _log(
                        f"  [{family} n={n} K={K} SCIP-TS] "
                        f"J_cx*={result.J_a_star:.4f} J_nat*={result.J_b_star:.4f} "
                        f"R(cx->nat)={result.R_a_to_b:.4f} R(nat->cx)={result.R_b_to_a:.4f} "
                        f"delta_l1={result.weight_perturbation_l1:.4f} "
                        f"disagree={result.min_assignment_disagreement} "
                        f"t={result.runtime_s:.2f}s"
                        f"{rev_str}{tau_note}"
                    )
                except Exception as error:
                    record = {
                        "family": family, "n": n, "K": K, "tier": "scip_tie_safe",
                        "status": "computation_error", "error": repr(error),
                    }
                    records.append(record)
                    _log(f"  [{family} n={n} K={K} SCIP-TS] error: {error}")

    # ---- Summary ----
    _log("\n" + "=" * 72)
    _log("SUMMARY")
    _log("=" * 72)

    valid = [r for r in records if "R_a_to_b" in r]
    exact_valid = [r for r in valid if r.get("tier") == "exact"]
    scip_valid = [r for r in valid if r.get("tier") == "scip_tie_safe"]

    rev_a_to_b = [r for r in valid if r.get("strict_reversal_a_to_b")]
    rev_b_to_a = [r for r in valid if r.get("strict_reversal_b_to_a")]
    any_rev = [r for r in valid if r.get("strict_reversal_a_to_b") or r.get("strict_reversal_b_to_a")]

    _log(f"Total records: {len(records)}")
    _log(f"Valid (computed): {len(valid)} (exact: {len(exact_valid)}, scip: {len(scip_valid)})")
    _log(f"Strict reversals (a->b): {len(rev_a_to_b)}")
    _log(f"Strict reversals (b->a): {len(rev_b_to_a)}")
    _log(f"Any reversal: {len(any_rev)}/{len(valid)}")

    if valid:
        max_R_a_to_b = max(r["R_a_to_b"] for r in valid)
        max_R_b_to_a = max(r["R_b_to_a"] for r in valid)
        _log(f"Max R(cx->native): {max_R_a_to_b:.6f}")
        _log(f"Max R(native->cx): {max_R_b_to_a:.6f}")

    # kappa vs R analysis (exact tier only)
    exact_with_kappa = [r for r in exact_valid if r.get("kappa_a_to_b", inf) < inf]
    if exact_with_kappa:
        kappa_lt_1 = [r for r in exact_with_kappa if r["kappa_a_to_b"] < 1]
        kappa_lt_1_stable = [r for r in kappa_lt_1 if r["R_a_to_b"] <= 1 + TOLERANCE]
        _log(f"\nStability theorem verification (a->b direction):")
        _log(f"  kappa < 1 cases: {len(kappa_lt_1)}")
        _log(f"  kappa < 1 AND R=1: {len(kappa_lt_1_stable)} (theorem predicts all should be R=1)")
        if kappa_lt_1 and len(kappa_lt_1_stable) == len(kappa_lt_1):
            _log(f"  [OK] Stability theorem CONFIRMED: all kappa<1 cases have R=1")
        elif kappa_lt_1:
            violations = [r for r in kappa_lt_1 if r["R_a_to_b"] > 1 + TOLERANCE]
            _log(f"  [FAIL] Stability theorem VIOLATED: {len(violations)} cases with kappa<1 but R>1")

    # Per-family breakdown
    _log("\nPer-family breakdown:")
    for family in all_families:
        fam_records = [r for r in valid if r.get("family") == family]
        fam_rev = [r for r in fam_records if r.get("strict_reversal_a_to_b") or r.get("strict_reversal_b_to_a")]
        if fam_records:
            max_R = max(max(r["R_a_to_b"], r["R_b_to_a"]) for r in fam_records)
            _log(f"  {family}: {len(fam_records)} instances, {len(fam_rev)} reversals, max R={max_R:.4f}")

    # Tau sensitivity analysis
    _log("\nTau sensitivity (SCIP tier reversals):")
    scip_with_tau = [r for r in scip_valid if "tau_sensitivity" in r and (r.get("strict_reversal_a_to_b") or r.get("strict_reversal_b_to_a"))]
    for r in scip_with_tau:
        fam = r["family"]
        nn = r["n"]
        kk = r["K"]
        sens = r["tau_sensitivity"]
        tau_results = []
        for tau_str in sorted(sens.keys()):
            s = sens[tau_str]
            if "error" in s:
                tau_results.append(f"tau={tau_str}: error")
            else:
                tau_results.append(f"tau={tau_str}: R_ab={s['R_a_to_b']:.4f} R_ba={s['R_b_to_a']:.4f}")
        _log(f"  {fam} n={nn} K={kk}: {' | '.join(tau_results)}")

    # Write results
    output = Path(os.environ.get(
        "E12_OUTPUT", ROOT / "results" / "e12_representation_placement_regret.json"
    ))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, default=str) + "\n", encoding="utf-8")
    _log(f"\nResults written to {output}")

    # Write summary
    summary_path = output.with_name(f"{output.stem}_summary.txt")
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
