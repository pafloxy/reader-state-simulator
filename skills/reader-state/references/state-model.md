# Reader model — contract 0.1

## What is modeled

The state is an explicit, inspectable hypothesis about a configured reader after a document prefix. It is not a hidden chain-of-thought dump, a proof certificate, or a measured psychological state. Store concise observations, state changes, questions, and evidence—not private scratchwork.

The run fixes the literal source, ordered units, reader preparation, source-backed or declared initial knowledge, strictness, model identifier, prompt version, isolation declaration, context policy, and sampling metadata when available. Initial knowledge (`K0`) does not change inside that run. Later state may revise earlier interpretations; earlier saved states remain unchanged.

## Positions and sources

With the ReaderSim adapter, `Lx.y` means sentence y inside top-level unit x; `Lx` means after top-level unit x. Top-level units can also be headings, code, math, tables, or other structures. The bridge uses an explicit mixed unit map; see input-contract.md for resolution rules. These are not physical file line numbers. The unit array's ordinal determines execution order; labels are unique identifiers for that frozen map. `L0` is the initial state. `unit_id` and Unicode codepoint spans `[start,end)` identify exact source content. Every non-whitespace source character must be represented. Unit IDs are stable within a revision, not automatically across revisions.

Each background entry is either a declared modeling `assumption` or an accessible `excerpt`, with text and limitations. Referencing an unread book does not supply that book. Missing evidence must remain missing. Supplied sources may conflict; preserve attributable alternatives instead of inventing agreement. A persona is not permission to attribute an unsourced fact to a paper.

## Registers

| Register | What each item records | Mandatory distinctions |
|---|---|---|
| `understanding` | A concept, proposition, interpretation, or currently learned relationship | `meaning`: unfamiliar/partial/understood; `justification`: background/explicit-definition/supported-argument/asserted/hypothesis/contested |
| `expectations` | An explanation, proof, bridge, or payoff still expected | Text and evidence; do not score importance numerically without calibration |
| `uncertainties` | Competing interpretations or unresolved doubt not necessarily a tracked issue | Preserve uncertainty rather than silently selecting an answer |
| `vocabulary` | A term and the reader's access to its meaning/use | `status`: named/explained/applied |
| `frame` | The currently perceived goal or organization of the explanation | Ground in the visible prefix, not the eventual manuscript plan |
| `load` | A qualitative hypothesis about explanatory burden | unknown/low/moderate/high; optional register contents, not a validated cognitive scale |

Every value carries `text` and nonempty `evidence`. The empty registers are legitimate: do not fill them merely to make a trace look complete. Meaning and justification are orthogonal. A reader may understand a theorem statement while still finding its proof unsupported. An explicit definition can be understood without establishing every theorem later claimed about it.

## Strictness

1. **Strict, default:** request a missing step unless it is already established or immediate from declared background.
2. **Moderate:** supply familiar routine steps; retain consequential gaps and ambiguities.
3. **Lenient:** proceed with charitable plausible connections, explicitly labeling assumptions.

None of these changes the evidence boundary, gives an undergraduate specialist expertise, erases a contradiction, or licenses invented citations. Familiarity and leniency must not be conflated. These policies are inherited design requirements, not empirically calibrated thresholds.

## Deltas and carry-forward

A proposal contains `updates` and `issue_events`. A register `put` names an item, a replacement value, a reason, and evidence. A `remove` requires an existing item and a reason. Items omitted from a delta survive unchanged. This prevents accidental loss caused by asking an LLM to regenerate a full cumulative state each step.

New items use run-local stable IDs, for example `K3`, `E1`, `V1`. Do not silently repurpose an ID to mean an unrelated concept. A substantive correction is an explicit new update with a reason. Earlier values remain visible in earlier records.

## Issues

Issue IDs follow `Q<number>.<origin-position>`, for example `Q1.L3` or `Q1.L1.3`. The number increases consecutively within a run. `introduced_at` is stored explicitly and must agree with the suffix. Identity across artifacts is `(run_id, issue_id)`.

Lifecycle: **open → resolve → reopen → resolve**. Opening requires category, question text, evidence, and current origin. A resolution or reopening retains identity and origin; it carries its own current step, reason, and evidence. A later resolution cannot change what was unresolved at an earlier prefix.

Categories: undefined-term, missing-prerequisite, missing-explanation, ambiguity, background-conflict, convention-difference, unsupported-claim, presentation. Issues and expectations overlap but are not identical: an expected theorem may be legitimate narrative suspense, not a writing defect. A query may assess whether a delay is harmful; the base trace need not condemn every open expectation.

## Evidence and uncertainty

Base evidence can reference a visible document unit, a declared background source, or the persona (`ref: reader`). A helper can check that a referenced item exists and is allowed. It cannot check that the text actually entails the observation, that the issue is genuinely useful, or that the modeled reader would behave that way.

Label a plausible reconstruction as a hypothesis. Do not confuse repetition with a proof or confidence with correctness. Do not generate numerical probabilities simply because the file format permits numbers elsewhere.

## Memory is a separate future policy

v0.1 offers full-prefix, trace-supported recall. This makes diagnostics inspectable but is not a realistic forgetting model. The persistent audit record and the modeled reader's accessible working memory are different objects. Future bounded-memory policies may filter what an isolated simulator can recall while preserving the full audit record for editorial inspection. Do not silently implement forgetting by deleting historical evidence.
