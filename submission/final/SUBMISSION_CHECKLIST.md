# Final submission checklist

## Scientific freeze

- [ ] Full pytest suite passes on the pinned environment.
- [ ] `reproducibility/verify_environment.py` passes.
- [ ] Canonical E12 summary reports 96 paired records and the manuscript table is generated from it.
- [ ] Main n=14, K=2 QPE witness matches the exhaustive audit and QCEC record.
- [ ] Six QFT single-solution apparent reversals match the exact-set audit and reduce to set-level R=1.
- [ ] `results/final_manifest.json` has zero SHA-256 mismatches.

## Manuscript QA

- [ ] Full `pdflatex -> bibtex -> pdflatex -> pdflatex` build succeeds.
- [ ] No undefined references/citations, overfull boxes, or stuck floats.
- [ ] `paper/certicut.pdf` and `paper/manuscript.pdf` are byte-identical.
- [ ] Bibliography has no missing or uncited entries; every reference supports the sentence in which it is cited.
- [ ] Data Availability cites the revision-specific Zenodo record once deposited.
- [ ] AI-use disclosure remains present and accurate.

## Public artifacts

- [ ] Push the frozen Git commit and release tag to GitHub.
- [ ] Create a new Zenodo version from the final reproducibility ZIP; record its version DOI/URL.
- [ ] Replace the prior-release-only wording in `CITATION.cff`, README, and Data Availability with the new revision-specific record.
- [ ] Rebuild PDF and release manifest after inserting the new Zenodo record, then create the final tag if the citation update changes tracked files.
- [ ] Upload the final arXiv source ZIP and verify the arXiv compilation preview.
- [ ] Set the GitHub homepage to the arXiv URL after the preprint is public.

## PRA resubmission

- [ ] Upload `paper/certicut.pdf` as the manuscript.
- [ ] Upload the cover letter from `submission/final/cover_letter_pra.md` after updating the revision-specific Zenodo sentence.
- [ ] Upload/provide `submission/final/response_to_referee_AV12884.md` if the workflow permits or requests a response to the prior report.
- [ ] Mention prior manuscript AV12884 in the submission history/cover letter.
- [ ] Verify authors, affiliations, corresponding-author email, section/PhySH metadata, funding, competing interests, and data availability in the submission form.

## Do not change after freeze unless necessary

Do not add new experiments, terminology, theorem claims, or references merely to enlarge the paper. Any post-freeze change must trigger the full tests, manuscript build, manifest regeneration, and package regeneration again.
