# Response to the previous referee report (AV12884)

We thank the referee for the critical assessment of the earlier version. The manuscript has been substantially rewritten and the numerical/reproducibility pipeline has been rebuilt. The major changes are summarized below.

## 1. Undefined terminology and difficult-to-follow statements

The earlier version used nonstandard terms such as “frozen,” “predeclared,” “auditable,” and “tie-safe,” and mixed scientific claims with artifact-governance language. Those terms have been removed from the visible manuscript. The revised paper uses standard optimization language: optimal set, cross-representation regret, feasible partition space, solver tolerance, lower/upper bound, and exhaustive enumeration.

The manuscript is now centered on one question: whether two semantics-preserving complete representations of the same logical circuit can induce different QPD-weighted optimal-placement sets when the feasible partition family and resource model are fixed.

## 2. Figure 1 and the claim of semantic equivalence

The original Figure 1 was replaced. The new figure uses the exact identity

RZZ_01(theta) = CX_01 [I tensor RZ(theta)] CX_01,

on the same logical wire pair. The logical unitary, logical wire set, and feasible partition space are therefore unchanged while the independent-QPD interaction weight changes. The three balanced four-qubit bipartitions can be evaluated analytically, and the figure caption gives the numerical log weights used.

The revised numerical records also store the semantic-verification method used for each representation pair. The main n=14 QPE witness is independently checked with MQT QCEC and reported as equivalent up to global phase.

## 3. Apparent AI-generated or template-like language

The paper has been rewritten around the scientific question rather than a framework or governance narrative. Numbered contribution lists, roadmap language, repeated caveats, and artificial terminology were removed. Supporting solver engineering, scaling experiments, and scope checks were moved to appendices and explicitly labeled as supporting rather than primary claims.

The manuscript transparently discloses the use of generative AI tools for implementation/debugging assistance, language editing, structural revision, and schematic-layout assistance. The authors executed the code, checked the outputs, and remain responsible for the scientific content and conclusions.

## 4. Excessive technical caveats and unclear main contribution

The revised main text is substantially narrower. Its central result is the distinction between comparing one optimizer-returned solution and comparing the complete optimal-placement sets. The quantity

Delta_{a->b} = min_{P in A_a} J_b(P) - J_b^*

is zero exactly when the source-optimal set and target-optimal set overlap. This removes false “representation changes” caused by arbitrary tie breaking.

The main positive witness is exact-QPE at n=14, K=2, with R(native->CX)=729. Exhaustive enumeration of all 1,716 balanced bipartitions confirms one optimum in each representation and zero overlap. The complementary negative result is QFT: six large single-solution apparent changes disappear under the set-level calculation, and exhaustive enumeration confirms a shared optimum in every case.

## 5. Reproducibility, public artifacts, and repository discoverability

The revised repository uses one canonical representation dataset with 96 paired records. The exact and medium tiers use the same symmetric near-balanced capacity policy. The medium-tier conclusions are checked across multiple optimal-set tolerances. The release contains exhaustive audits for the main QPE witness and all six QFT degeneracy cases, environment pins, regression tests, and a SHA-256 manifest.

The current validation state is:

- 175 automated tests passing;
- 96 canonical paired representation records;
- 8 set-level changes in the fixed benchmark corpus (3 exact-QPE and 5 Grover stress cases);
- all 48 medium-tier records stable across the tested optimal-set tolerances;
- the n=14, K=2 QPE headline result independently reproduced by exhaustive enumeration;
- all six QFT apparent changes independently shown to have nonempty optimal-set intersection.

The GitHub repository metadata and README have also been revised so that the paper, canonical data, reproduction commands, and prior Zenodo record are directly identifiable.

## 6. Reference coverage and positioning against prior work

The Related Work section was rewritten and the bibliography re-audited. The revised manuscript explicitly cites work on decomposition-aware cutting, automatic cut placement, joint and communication-assisted cutting, scalable partitioning, routing/hardware-aware cutting, and sampling-overhead optimization. In particular, the revised text does not claim that decomposition can affect circuit cutting or that graph partitioning is new.

The claimed contribution is narrower: two complete semantics-preserving representations are compared under the same logical wire set, feasible partition family, and independent-QPD resource model, and the comparison is made at the level of the complete argmin set rather than one optimizer-selected solution.

## 7. arXiv and archived release

The submission package now includes a clean arXiv source bundle. The previous Zenodo DOI (10.5281/zenodo.22005561) is explicitly identified as a prior release rather than as the exact evidence bundle for the revised paper. A revision-specific archive containing the corrected canonical data, tests, and integrity manifest is prepared for deposition as a new Zenodo version.

## 8. Summary of the scientific revision

The revised manuscript no longer presents a broad circuit-cutting framework as its principal contribution. It instead tests and formalizes a specific representation-sensitivity question. The principal theoretical statements are elementary perturbation/stability consequences tailored to this objective; they are not presented as new generic optimization theory. The main empirical claims have independent exhaustive or equivalence-checking support, while deeper Grover cases are explicitly demoted to stress tests because their semantic verification is weaker.
