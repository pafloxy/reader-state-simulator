# Milestones and release gates

## M0 — grounded skill package: released in v0.1.0

Inspected the supplied source subset and operating records. Preserved the six actual ReaderSim Python files. Retained the RC1 state store unchanged. Added source preparation, source provenance, label-based state queries, and a compact runtime skill. Retained RC1 trace compatibility and tested the new bridge, including copying the skill alone to an independent directory. 90 tests passed locally; the fixture demonstration saved and queried five units and kept later clarification separate.

This is the public protocol-alpha release, not a real model-host evaluation.

## M1 — operationally validated host workflow: next

**Definition of done:** A new agent session, without the project backstory, loads the released skill, prepares a short approved passage, produces reader deltas through a real host, saves them, exits, and answers later human/agent inquiries from the same saved run.

| Gate | Required evidence | Current state |
|---|---|---|
| Reconcile the real local checkout | Diff and source hashes; preserve unuploaded work and operating histories | Six local source modules match the packaged hashes byte-for-byte |
| One host can invoke the helpers | Install/discovery and actual execution receipt | Helper directory portability tested; host activation untested |
| Real bounded inference | Submitted payloads, model outputs, tool-access policy, canary checks | Untested; no provider invoked here |
| Reuse across sessions | Fresh session loads prior run; queries do not rebuild base; dialogue stays separate | Deterministic process test passed; real agent test pending |
| Honest public contents | License selected; allowlisted source; synthetic example; no private logs/manuscript | Released under MIT from a clean allowlisted subtree |
| Useful pilot | At least one located diagnosis checked by an author and a corresponding bounded edit | Not yet evaluated |

Use Markdown, one reader, a short passage, one supported host, and block granularity unless the pilot specifically needs sentence positions. Label the actual isolation mode. A protocol-preview release can be labeled as such before host completion, but must not claim an operationally validated isolated simulator.

Do not block M1 on recovering old experimental manuscripts. Their source-specific conclusions cannot be revalidated here, but the synthetic clean-room workflow can be tested independently. Do not close the old TeX-quality ticket merely because Markdown is enough for M1.

### Local implementation order

Install the standalone skill into a disposable target project, not globally. Bind the host's one fresh-context inference capability; do not build a provider abstraction framework. Run the two-session test with a suffix canary and an instruction embedded in source data. Record actual calls, outputs, failures, token/cost information when available, and final artifact paths. Fix contract failures, run all tests again, and publish a patch release only after reviewing the same public boundary.

## M2 — reliability and coverage, after a usable alpha

Prioritize from pilot evidence, not a speculative feature catalog. Future work includes source-format adapters with visual/linked-artifact provenance; input segmentation improvements; useful stable IDs across revisions; conservative unchanged-prefix reuse; faster indexed queries/checkpoints; stronger crash recovery; and additional host bindings. Keep schema migrations explicit and existing runs readable.

The recorded TeX normalization problem remains open. Rich legacy experimental import requires recovering actual artifacts and demonstrating that exposure timing, stable issue IDs, and reference provenance survive the mapping.

## M3 — evaluate the central hypothesis

Compare ordinary unstructured critique with the skill-based workflow on held-out passages. Measure located useful findings, false alarms, trace consistency, costs, and human-checked improvements. Test audience/background changes and strictness separately. Evaluate whether later query reuse saves total work without amplifying unsupported prior answers.

No numeric cognitive score, population-fidelity claim, or writing-quality improvement is established by passing storage tests. Cross-model or real-reader evidence must have its own experiment and report.

## Open questions: release blockers versus research

| Question | Release handling |
|---|---|
| Can the first host prevent author-history/future-source exposure? | M1 blocker for an isolated claim; verify or label instruction-only |
| Which current local files supersede the uploaded subset? | Inspect before applying changes; do not guess |
| Which license will the maintainer adopt? | Resolve before public distribution |
| How fine should compilation be? | Freeze per run; support block or sentence now; evaluate quality later |
| Can a query be answered from retained state alone? | Retrieve first; bounded interpretation second; otherwise insufficient |
| Are later answers reliable enough to reuse? | Preserve source/scope and distinguish interpretation from evidence |
| Does this model real readers or improve writing? | Open empirical question, not a prerequisite to release a clearly labeled diagnostic tool |
| How should forgetting and long-paper contexts work? | M2/M3; full-prefix policy is explicit in alpha |
