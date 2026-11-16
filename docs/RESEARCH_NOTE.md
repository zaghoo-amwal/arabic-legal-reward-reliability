# Research note: reward reliability in Arabic legal drafting

## Experimental status

Six tasks; 109 weighted criteria; one saved answer per model per task. Candidate labels are GPT-6 Astra through Codex (high reasoning) and Claude Opus 5.5 through the existing provider runner. Full scores use the project's Claude judge. Requested model labels are experiment configuration, not independent attestation of backend model identity.

The table is transcribed from the saved full-score JSON artifacts. It records raw historical rewards, including known grading errors. No new generation or judging was performed for this documentation update.

| Task | Astra raw | Claude raw |
|---|---:|---:|
| `consulting_contract_review` | 0.7250 | 0.7500 |
| `maintenance_contract_review` | 0.7738 | 0.8571 |
| `partner_exit_meeting_prep` | 0.7300 | 0.8333 |
| `payment_demand_letter` | 0.4596 | 0.8485 |
| `probation_termination_memo` | 0.4394 | 0.3788 |
| `mutual_nda_drafting` | 0.2947 | 0.7636 |

## Three observed failure modes

1. **Negation and semantic scope.** Payment and NDA traps matched prohibited-action wording inside statements rejecting that action. The NDA raw reward was 0.2947, with base score 0.5894 and gate factor 0.5. This is a concrete example of a grading error amplified by reward aggregation.
2. **Contractual versus statutory conditions.** The probation response discussed a contract that specifies 90 days while also stating a 180-day statutory ceiling. The trap treated the conditional discussion as outdated law. A correct evaluator needs to distinguish these claims.
3. **Hidden requirements.** The NDA task metadata specifies SA, but the generation prompt does not. Saudi-specific rubric items therefore evaluate an unstated requirement. Fixing the prompt requires new generations; silently reinterpreting historical outputs is insufficient.

Other observed misses include Arabic paraphrases for prior possession and proof, bracketed duration placeholders, and semantic section separation. These examples motivate measuring verifier errors against independent annotations.

## Follow-up: trap verifier validation (2026-11-16)

The first two failure modes were measured and addressed in [`experiments/verifier_validation`](../experiments/verifier_validation/README.md). The test set is 67 matched Arabic sentences for six traps, frozen (SHA-256 recorded) before any change and split 37 dev / 30 held-out. The historical checker wrongly penalised 17/37 compliant sentences and missed 10/30 violations. Clause-scoped negation, designed on dev errors only, scored 0/17 false penalties and 1/13 misses on the held-out split, measured once.

Re-scoring the private corpus with the fixed checker changed three raw rewards, all known false positives: Astra payment 0.4596 → 0.7172, probation 0.4394 → 1.0, NDA 0.2947 → 0.6621. No reference, negative-control or Claude decision changed. The historical table above is kept as recorded; these are corrected-grader reruns of the same saved answers, not new generations. The third failure mode (hidden jurisdiction requirement) is still open.

Caveats: an AI assistant wrote and labelled all the sentences, both splits come from that one author, and the held-out sample is small. These results establish that the checker change generalises within this set, not that it is legally validated.

## What the evidence does and does not support

The tests exercise normalization, reference/control separation and selected traps. Eleven tests passed in the original local environment before release preparation; those private-corpus tests are not included here. This is implementation evidence, not a precision/recall estimate or independent legal validation.

The source references have unequal completeness, and some legal claims are provisional. Rubrics were adapted after seeing candidate answers, so results are development-set measurements. Different generation harnesses, one sample per task, a Claude judge, and known false positives prevent a reliable model ranking. Differences between two judges alone do not establish self-preference causally.

Earlier manual adjustments to two Astra trap results were sensitivity analyses, not corrected-grader reruns. The follow-up above replaces them with actual reruns under a frozen, tested checker; the historical raw scores are still reported unchanged.

## Next experiment (proposed, not completed)

Freeze a new prompt/rubric version with explicit jurisdiction. Build matched pairs that vary only negation, contractual versus statutory framing, or Arabic paraphrase. Include both valid answers and nearby invalid answers, so fixing false positives cannot be achieved by accepting everything.

Have independent qualified reviewers label criterion satisfaction while blinded to model identity. Separate development examples from held-out examples before changing patterns. Measure per-criterion precision/recall, false gate activation rate, score stability under meaning-preserving rewrites, and agreement with human judgments.

Then regenerate multiple answers per task with matched prompts and tool access; record model/settings and report uncertainty. Keep human assessment separate from deterministic and LLM-judge scores. Any RL optimization experiment should follow verifier validation and test for reward exploitation on held-out tasks.

## Reproducibility boundary

The source-derived six-task corpus and full model-run evidence are withheld from this release. The table above is a summary of local historical results, not a publicly reproducible leaderboard. The included synthetic example reproduces the mechanism of a negation-sensitive trap failure using newly authored text. It is not a rerun of any historical model or task.
