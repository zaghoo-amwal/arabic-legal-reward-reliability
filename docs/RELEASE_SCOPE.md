# Public release scope

Included: evaluator source code; a newly authored AI-assisted synthetic prompt, reference and rubric; offline tests; summarized historical research findings, a machine-readable score summary, a research cover page with public literature links and a short author background, technical methods, and a publication checker.

Excluded: all six original task packages and references, original negative-control fixtures and citation ledger, screenshot/document provenance, raw model answers, judge caches, snapshots, Codex event traces, session metadata, local logs, and application/resume working notes.

The original working directory is retained locally. This standalone folder is the publication source; do not upload its parent directory. The source workspace had no Git history to scrub. Publication starts from a new repository containing only the reviewed release files.

Historical raw scores remain unchanged. The synthetic demonstration is separately labeled and deliberately retains a known verifier defect. Provider adapters are historical and unverified against current services; the validated release path is the offline demo.

No license or ownership claim has been invented. Choose a code license and provide an accurate contributor statement if you want to distribute this as an open-source project. Source-derived material can be added later only after resolving its redistribution rights.

Before committing, run `python3 tools/check_release.py`, inspect the staged diff, and ensure only this folder is being added. The checker covers common secret formats, local user paths and prohibited artifacts; it is not a guarantee against every possible sensitive string.
