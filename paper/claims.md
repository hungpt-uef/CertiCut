# CertiCut Claim Audit

## C1 K-Way Solver-Tolerance Bounds

Claim: For independent-QPD capacitated K-way partitioning, a solver-tolerance feasible incumbent and global bound pair imply the reported model-overhead factor `F = exp(UB-LB)`.

Evidence: K-way formulation tests; E9 144-run replicated heterogeneous matrix; E7 K=2 backend audit; existing safe-boundary reference tests.

Scope: arbitrary declared K, stated lower/upper capacities, specified independent-QPD cost model; reference safe-boundary claims remain K=2.

Limitation: runtime bounds use floating-point solver tolerances, not independently verified numerical certificates.

## C2 Polyhedral Strengthening

Claim: B2S root strengthening substantially improves controlled proof completion.

Evidence: Phase 6.2 controlled ablation, `41/90 -> 90/90` proofs within 100 nodes.

Scope: synthetic CNOT exact-balanced hard rung, controlled methods.

Limitation: root processing can dominate runtime near n=40.

## C3 Gate-Dependent Sampling Objective

Claim: independent QPD gate costs can change preferred cut plans relative to cut count.

Evidence: Phase 6.5 CS/CX and iSWAP/CX counterexamples; controlled E5 identity-free corpus (16/120 strict reversals); E6 predeclared MQT Bench algorithm-derived audit (6/36 strict reversals across Draper QFT adder and exact QPE).

Scope: Qiskit Addon Cutting 0.10 independent QPD decomposition model.

Limitation: E6 establishes existence/relevance on a fixed 36-circuit algorithm-derived corpus, not workload prevalence, hardware routing, joint-QPD, or globally optimal arbitrary-gate decomposition.

## C4 Native Representation Sensitivity

Claim: legal native-QPD versus CX-normalized representations can materially alter predicted sampling overhead estimates.

Evidence: Phase 6.5B paired fixed-pi/4 QAOA source circuits; BV/VQE controls.

Scope: paired MQT Bench sources, Qiskit Addon Cutting 0.10.0 cost model.

Limitation: not an intrinsic shot-complexity claim for abstract algorithms.

## C5 Practical-Qmax Scope Analysis

Claim: no measurable K=2 sampling penalty occurred on the initial Qiskit-proven practical matrix.

Evidence: Phase 6.4A+ `24/24 F_K2=1` within tolerance.

Scope: QAOA/BV/VQE, n=8/12/16, specified Qiskit practical search records.

Limitation: not general K=2 equivalence; general-K is deferred.

## C6 E9 Replicated Scaling Boundary

Claim: The baseline SCIP assignment/locality MIP supports heterogeneous independent-QPD K-way instances through n=60, with closure dependent on K and graph family.

Evidence: E9, 144 records over three families, n in {20,32,40,60}, K in {2,3,4,5}, three fixed seeds/cell, 10 s single-thread limit; 101/144 solver-tolerance closures and finite factors on open records.

Scope: three fixed deterministic seeds per family-size-K cell; exact near-balanced capacities; Qiskit Addon Cutting 0.10 independent-QPD registry.

Limitation: not a prevalence estimate, custom solver comparison, universal large-K scalability claim, or verified numerical proof.
