# Frozen semantics, v0.1 bindings

## Product boundary

The product is the reusable reading method plus an inspectable artifact contract. The agent, not a new application, is the default interaction surface. Helpers provide deterministic storage and projection. The host supplies inference and its isolation/privacy policy. A future CLI front end, Obsidian integration, MCP tool, or UI is a consumer, not the definition of the reader model.

## Module map

```text
#ReaderState(@document, @reader, @config)
|
+-- ##PrepareSource          -> @prepared_document
|   <original normalizer; exact mapping; review warnings>
|
+-- ##CompileReader          -> @base_trace
|   |
|   +-- ##BuildBoundedContext -> @ticket, @reader_payload
|   +-- ##InferReaderDelta    -> @delta
|   |   <host supplied; not implemented by a deterministic script>
|   +-- ##ValidateAndCommit   -> @next_snapshot
|
+-- ##QuerySavedState        -> @recorded_or_derived_answer
|
+-- ##AppendInquiry          -> @inquiry_history
    <never changes @base_trace>
```

File mapping:

| Module | Implementation |
|---|---|
| PrepareSource | `scripts/readersim/normalization.py` plus `scripts/document_adapter.py` |
| BuildBoundedContext | `TraceStore.context` in `scripts/reader_store.py` |
| InferReaderDelta | Host capability; instructions and contract supplied, integration untested |
| ValidateAndCommit | `TraceStore.commit` / `reduce_delta` |
| QuerySavedState | `ReaderSkillStore.state_at` / `query_at`, plus base `get` / `compare` |
| AppendInquiry | `open_session`, `append_exchange`, `conversation` |

These are modules with contracts, not six autonomous agents. A single orchestrator can call all deterministic modules and one isolated inference capability.

## What is frozen from the discussion and recorded prior design

For a fixed document revision, reader/background, and configuration, compile a reusable trajectory. The historical reader sees only the prefix and declared background. Save explicit changes with provenance; preserve cumulative state and stable issue identity. Understanding a claim differs from accepting its justification. Strictness differs from expertise. Later conversation can supply clarification only in its own explicitly resumed session. Initial knowledge and earlier snapshots remain frozen. Human and agent inquiries use the same stored base trace.

## What v0.1 chooses as implementation, not eternal architecture

Local JSON files, random run IDs, content-addressed preparations, a Python helper, block/sentence input policies, explicit mixed unit maps, full-prefix contexts, full snapshots, and a default short-passage limit are replaceable implementations. Schema versions and provenance make changes explicit. They must not be described as all having been approved in the earlier September design discussions.

The state store does not independently generate semantic knowledge. It validates shapes, evidence availability, transition order, immutable identity, hashes, and deterministic replay. Semantic entailment, usefulness of a criticism, persona fidelity, prompt-injection resistance, and genuine host isolation require additional checks.

## Query semantics

Exact retrieval is deterministic. New interpretation may call a model over bounded saved evidence. An unsupported question returns insufficient record. No query should silently trigger a complete base simulation. A different audience needs a different run; a hypothetical editorial comparison is not that audience's historical trace.

`base` inquiry records can be reused as records of questions/interpretations by the orchestrator, but do not become inputs to the original reader. `dialogue` deliberately accumulates conversational additions. `editorial` identifies analyst work. Promoting a useful clarification into background is an explicit new reader/config/run.

## Prefix isolation

The orchestrator can know the entire manuscript. The simulated reader cannot receive that orchestrator's history as part of a supposedly isolated call. Give the worker only the versioned instructions, schema, and bounded payload. Disable broader document lookup and inherited planning history. A `context_hash` records what the helper produced, not every message or tool the host added. `instruction-only` is an honest fallback mode, not the same assurance.

A deterministic prefix boundary cannot suppress pretrained knowledge; that is a different fidelity issue. Likewise, copying full source into a private preparation is not itself a leak provided workers cannot read it. Source paths or filenames are not sufficient access controls.

## Future extension points

Input adapters can add approved rich-document records without altering inquiry semantics. Host adapters can replace inference transports while preserving the delta contract. Indexed materializations/checkpoints can replace replay for performance while retaining historical truth. Revision maps can enable verified prefix reuse; until then, new revisions get new runs. A memory policy can limit modeled recall while preserving the complete audit trace. Evaluation can compare structured simulation with ordinary critique without conflating engineering conformance and human accuracy.

Do not build those modules before the smallest complete host workflow is tested.
