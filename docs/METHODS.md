# Methods and evaluation boundaries

## Two distinct artifacts

The original local study contains six Arabic legal tasks, 109 weighted criteria, source-derived references, and saved candidate outputs. This public release contains evaluator source plus one newly written synthetic task with seven criteria. Public demo results must not be mixed with the historical benchmark table.

Historical prompts were transcribed from source material, including a cropped prompt reconstructed with limitations. Three comparison references were full documents and three were chat summaries. These references are not independent ground truth. Rubrics were adapted after reviewing candidate outputs, so the study is exploratory and cannot measure held-out generalization.

## Scoring

Arabic normalization folds selected orthographic variants, digits and written article ordinals. Deterministic checks evaluate pattern matches, coverage, counts, traps, language ratio, citation ranges and an allowlist of case identifiers. Traps can excuse a hit through a framing pattern within a character window, through clause-scoped negation (`clause_negation`: a negator governing the hit inside its own clause, excluding deontic «لا يجوز» and affirmative «لا شك»), or through a same-sentence cue (`sentence_unless`, e.g. a contractual term rather than a statutory rule). The negation rule was validated on frozen held-out sentences ([experiment](../experiments/verifier_validation/README.md)). A citation-range check only tests a numerical boundary; it does not establish that the provision exists, is current, or supports the answer.

Judge criteria use normalized scores of 0, 0.5 and 1. The reward is a weighted average of scored criteria multiplied by each failed gate's multiplier. A partially satisfied gate also activates its multiplier. Without the judge, unscored judge items leave the denominator, so full and rules-only scores are not directly comparable.

Existing implementation limitations include incomplete judge replies being treated as unscored criteria and a cache key that does not incorporate every judge input, including reference text and system instructions. These need resolution before treating future judged runs as a robust evaluation service. Historical scores have not been recomputed or silently corrected.

## Generation and judging

The historical Astra runs requested GPT-6 Astra with high reasoning through Codex, with tools disabled and transcript events audited locally. Codex's system instructions still apply. Claude candidate generation used a separate provider adapter. The project used a Claude judge rather than independent expert adjudication. One candidate per model per task does not estimate variance or permit confident model rankings.

Provider scripts retain historical model identifiers and account-dependent beta/CLI options. These adapters were not live-tested for the public release. The validated public path is offline. Optional API generation requires the Anthropic SDK in `requirements.txt` and `ANTHROPIC_API_KEY`; the public client neither reads local key files nor prints credentials. Codex requires its own installed and authenticated CLI. Generated files remain excluded from Git by default.

The synthetic task has no judge criteria. Running it with `--judge` does not constitute a new model experiment.

## Proposed validation protocol

1. Version prompts, source evidence, rubric definitions and grader code together. Put jurisdiction and date in the model-visible task where relevant.
2. Create positive/negative matched pairs, including negation and paraphrase variants. Have qualified reviewers independently label criterion satisfaction while blinded to model identity.
3. Separate development and held-out examples before revising the verifier. Report per-criterion precision/recall, false gate activation, human agreement and score stability under meaning-preserving edits.
4. Use matched model harnesses and multiple samples. Estimate uncertainty at the task level; correlated rubric items are not independent task samples.
5. Before RL training, measure whether optimizing the reward encourages shortcuts. Evaluate on held-out tasks and independently verified outcomes.

This is a proposed protocol. No independent legal adjudication, held-out validation study, financial-task benchmark or RL training result is claimed here.
