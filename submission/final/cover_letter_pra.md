Dear Editors,

Please consider our manuscript, **“Representation Dependence of Optimal Cut Placement in Quasiprobability Circuit Cutting,”** for publication as a Regular Article in *Physical Review A*.

This submission is a substantially revised version of our earlier manuscript AV12884. We have narrowed the paper to one question: when two complete gate-level representations implement the same logical unitary, with the same logical wire set and the same feasible fragment family, can the representation alone change the cut placement that minimizes a fixed independent quasiprobability-decomposition (QPD) resource model?

The main contribution is a set-level formulation of this question. Rather than comparing one optimizer-returned partition from each representation, we compare the full optimal-placement sets through cross-representation regret. This distinction is necessary because degenerate optima can otherwise create false representation changes. In our numerical study, an exact-QPE instance at n=14 and K=2 gives a genuine modeled-overhead ratio R=729 under this criterion. An independent exhaustive enumeration of all 1,716 balanced bipartitions confirms unique, disjoint optima, and MQT QCEC independently verifies the two circuit representations as equivalent up to global phase. By contrast, six apparent QFT changes produced by comparing single solver outputs disappear under the optimal-set comparison; exhaustive enumeration confirms a shared optimum in every case.

We do not claim that decomposition-aware cutting, graph partitioning, or QPD circuit cutting is new. The revised Related Work section now explicitly positions the manuscript against prior work on decomposition-aware cutting, automatic cut placement, joint and communication-assisted cutting, scalable partitioning, and sampling-overhead optimization. The contribution is narrower: representation-dependent changes of the QPD-weighted argmin set under a fixed feasible partition space and resource model, together with a set-level comparison that removes optimizer tie-breaking artifacts.

The revision also addresses the presentation and reproducibility concerns raised on the previous submission. We replaced the original schematic with a verified semantics-preserving identity, removed undefined or nonstandard terminology, reduced technical caveats in the main text, corrected and expanded the bibliography, and rebuilt the numerical release around one canonical 96-record representation dataset. The repository includes regression tests, exhaustive audits for the main QPE witness and the QFT degeneracy cases, environment pins, and SHA-256 integrity manifests. The complete test suite currently passes 175 tests.

The authors are responsible for all scientific content and conclusions. The manuscript contains a transparent disclosure of the use of generative AI tools for implementation/debugging assistance, language editing, structural revision, and schematic-layout assistance.

The revision-specific software/data archive is publicly available as CertiCut v2.0.0 at Zenodo DOI 10.5281/zenodo.23205464. It contains the canonical data, exhaustive audits, regression tests, and integrity manifest supporting this revision.

Thank you for your consideration.

Sincerely,

Phung Trong Hung
Faculty of Information Technology, Ho Chi Minh City University of Technology (HUTECH)
Contact: phungtronghung0808@gmail.com

Huong Bui
Faculty of Information Technology, Ho Chi Minh City University of Technology (HUTECH)
