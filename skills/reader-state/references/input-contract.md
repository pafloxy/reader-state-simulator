# Input preparation — ReaderSim bridge v1

This release reuses the supplied `readersim` Python sources unchanged. The bridge adapts those sources to the trace store; it does not implement a competing Markdown parser.

## Supported first-release path

Native UTF-8 `.md` / `.markdown`, or the original native-Markdown `readersim.normalized-document.v0.2` JSON. Non-Markdown sources are refused by the new helper. Existing conversion code remains available to a developer, but is not invoked automatically by the skill. The input cap is 5 MiB; run `max_units` and host token budgets can be stricter.

The parser is conservative and source-oriented, not a full Markdown renderer. Inline notation, code, mathematical source, tables, HTML, and link syntax can remain literal. A warning is not a successful visual interpretation. Missing images, citation bodies, or external notes are not silently fetched or treated as read. A document containing those features can be used only with that explicit representation limitation, or prepared externally into a reviewed self-contained representation.

The original linked manuscript specimen is a different experimental artifact contract. The bridge refuses unknown top-level/unit extensions rather than stripping figure/equation/reference records. Importing that specimen is future work requiring its actual bytes and compatibility tests.

## Source projection

`prepare` freezes input bytes by hash, normalizes newlines, and invokes the original normalizer. It removes only recognized initial YAML frontmatter from the *reader-visible* source; metadata content is not passed to the reader. Source provenance records the original source hash, normalized hash, body offset, original kinds, exact normalized-source spans, and warnings. Original absolute filesystem paths are not copied into preparation content.

The trace document's `source_text` is the reader-visible body, with exact codepoint spans. A separate source map relates those spans to normalized-source offsets. Every non-whitespace character of the reader body must be covered. UTF-8 byte hashes and Unicode-codepoint offsets have different meanings and must not be interchanged.

Legacy JSON imports verify the normalized text hash and consistency of the recorded source hash/revision. They cannot independently verify original source bytes that were not supplied. That limitation is recorded. Malformed maps, overlapping projected spans, missing body content, unsupported kinds, and richer linked-artifact formats are refused.

## Granularity and addresses

`block`: one step per original top-level unit, preserving its `unit_id` and `Lx` label. Top-level units include headings and structures, not just prose paragraphs.

`sentence`: one step per available sentence child (`Lx.y`), with code/math/tables/headings retained as whole top-level units. The trace uses `granularity: explicit` because it can mix sentence and structural boundaries. This does not add a sentence splitter; it uses the original heuristic. Review its segmentation on actual mathematical prose.

`L0` retrieves initial knowledge. Dotted and hyphenated aliases are canonicalized by the original routine. A block-end request in a verified sentence projection resolves to that block's last sentence, with the resolution reported. A sentence request in a block-only run returns `BOUNDARY_MISSING`; it must not use the later block state. Existence of a text address does not imply a compiled reader snapshot exists there.

## Preparation and binding persistence

```text
.reader-state/
  prepared/
    prep-<content-hash>.json      private immutable normalized input + source map
  run-<uuid>/
    run.json                    immutable reader/config/document
    preparation.json            checked binding to the exact prepared input
    trace/...                   committed semantic deltas + snapshots
    inquiries/...               separately anchored later discussion
```

The preparation store is not a reader's memory. It can contain the complete body and source metadata. Never hand it to a prefix-isolated worker. Only `context` or `query_at` payloads are worker inputs.

`create_prepared` requires a declared representation review. `reviewed: true` is a caller assertion, not machine proof of fidelity. It reuses a unique identical preparation/document/reader/config match by default; `reuse: false` explicitly requests a new sample. Multiple existing matches produce `AMBIGUOUS_RUN`, not arbitrary selection.

Preparation writes are atomic and no-overwrite. Creation of the run and its preparation binding is not a multi-file transaction. An interruption between them can leave a valid base run without a binding. It is never automatically reused as a prepared run. `verify` reports the absence; quarantine/recreate after inspection. This reference is for a trusted local single-orchestrator workspace, not hostile multi-user or distributed storage.

## Compatibility

The existing trace schema remains `0.1`. This release adds preparation/binding schema versions and helper operations without changing historical trace records. `reader_store.py` remains byte-identical to RC1. Tests retain RC1 authored fixtures and saved traces.

A future input adapter must preserve document coverage, exact provenance, unit identity within a revision, and exposure order. Cross-revision stable identity, rich linked artifacts, semantic equivalence to rendered documents, and incremental recompilation are not claimed here.
