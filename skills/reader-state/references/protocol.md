# Artifact protocol and reference binding — 0.1

Version 0.1 adds the `reader_state.py` facade and preparation/binding records described in `quickstart.md` and `input-contract.md`. This document describes the unchanged base store. The facade supports all of its operations. Raw `create` always creates a new run; `create_prepared` implements checked unique reuse.

This is a local reference implementation, not a service. `reader_store.py` has no model SDK or network calls. It receives semantic proposals from a host agent, applies structural checks, and returns JSON. Its runtime uses Python's standard library and POSIX file locking/hard links. Windows, network filesystems, hostile concurrent writers, and very large manuscripts are not supported claims.

## Identities and files

```text
<project>/.reader-state/
  run-<uuid>/
    run.json                  immutable inputs, versions, initial reader
    trace/
      000001.json             committed delta + validated snapshot
      000002.json
    inquiries/
      session-<uuid>/
        session.json          immutable anchor and query mode
        events/
          000001.json         question, answer, additions, evidence
```

Writer lock files are operational files, not semantic artifacts. Temporary files are ignored. The frontier is the contiguous sequence of committed step files; there is no second mutable frontier file to become inconsistent.

A run has a random `run_id` and an `input_digest` covering document, reader, and configuration. Equal input digests identify matching configurations, not identical stochastic outcomes. Recompiling identical inputs creates a distinct run. Reusing a run is an explicit choice. A Python host can compute `digest({"document": document, "reader": reader, "config": config})` and pass it to `list_runs(input_digest=...)` before creating a new run; do not create a fresh run merely to obtain that digest. No implicit “latest run” changes historical query meaning.

The manifest includes the literal source and lossless units, reader/background/K0, model and prompt identity, context policy, declared isolation, and any sampling metadata available. The host must bind `prompt_version` to immutable prompt/schema instructions and preserve their actual content with its integration evidence; this helper has no separate prompt registry. The context hash covers the helper-produced bounded payload, not all messages a host might attach. Model names that are mutable aliases should be recorded as such; unknown provider details must remain unknown. Parent run IDs can record lineage, but automatic prefix reuse is not implemented.

Stable JSON encoding is `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`. SHA-256 covers these UTF-8 bytes. This is a project-specific encoding, not a claim of RFC 8785 interoperability. Other-language adapters must reproduce this encoding or revise the schema through an explicit migration.

## One canonical transition, one stored projection

Each step stores its `delta`, `snapshot`, predecessor hash, context hash, and proposal digest in one file. The delta is canonical change history. The snapshot is a materialized projection checked against deterministic replay, not an independently editable second truth. Issue lifecycle history occurs only in `delta.issue_events`; prefix issue lists are derived.

Full snapshots are intentionally retained for the small first release. If accumulated state grows linearly, total snapshot storage can grow quadratically. The reference `get` replays/validates the selected prefix rather than offering indexed constant-time retrieval. This costs local I/O and computation but **zero model calls**. Selective returned registers reduce agent context, not replay work. Optimize only after measuring real use.

## Operation surface

The Python API is `TraceStore(root)`. The command binding accepts one JSON request, through standard input or `--request PATH`:

```sh
python3 skills/reader-state/scripts/reader_store.py \
  --root .reader-state --request request.json
```

Successful responses are `{"ok":true,"result":...}`. Expected failures are `{"ok":false,"error":{"code":"...","message":"..."}}`, exit status 2. The CLI is an internal binding and debugging route, not the product's human interface.

| `op` | Other request fields | Meaning / write effect |
|---|---|---|
| `create` | `document`, `reader`, `config` | Validate inputs and create an immutable run manifest |
| `list` | optional `input_digest` | Find saved runs; no model call |
| `context` | `run_id` | Return the next allowed prefix plus previous state and issues; no inference |
| `commit` | `run_id`, `proposal` | Validate a sequential proposal and publish one step atomically |
| `get` | `run_id`, `step`, optional `registers` | Exact saved state and derived issues at a prefix |
| `query_context` | `run_id`, `step`, optional `session_id` | Bounded prefix, reader, snapshot, and explicitly resumed dialogue history |
| `compare` | `run_id`, `first`, `second` | Deterministic added/removed/changed state items; editorial scope |
| `open_session` | `run_id`, `step`, `mode` | Create an anchored base/dialogue/editorial inquiry session |
| `conversation` | `run_id`, `session_id` | Retrieve that session and validate its event chain |
| `append_exchange` | `run_id`, `session_id`, `expected_head_hash`, `exchange` | Append a question/answer with provenance, without changing base history |
| `verify` | `run_id` | Check structural consistency, prefix references, chains, replay, sessions |

The compact agent-level vocabulary is **initialize → advance → inspect → record**. The lower-level calls above make failure handling explicit; there is no need for a generic database query language.

### Advancing a run

`context` returns `step`, `expected_parent_hash`, `context_hash`, and `context`. Give only `context` to the isolated simulator. The host retains the ticket. The simulator returns a `delta`; the host creates:

```json
{
  "op": "commit",
  "run_id": "run-example",
  "proposal": {
    "step": 3,
    "expected_parent_hash": "<the exact returned hash>",
    "context_hash": "<the exact returned hash>",
    "delta": {
      "updates": [],
      "issue_events": []
    }
  }
}
```

This illustration uses placeholders, not a runnable ticket. Use actual values; do not let the model fabricate hashes. A model can legitimately propose an empty delta when a unit adds nothing material. Validation does not prove that this omission is semantically adequate.

Invalid references, missing fields, invalid issue transitions, and wrong context tickets fail before publication. Identical retries return the existing record. A different proposal for an occupied step returns `CONFLICT`. Never resolve a conflict by editing the existing file; reload the frontier or create another run.

### Publication and recovery

While holding a local advisory writer lock, serialize the whole record to a temporary file in the destination directory, flush and fsync it, and hard-link it to the final filename. Link creation cannot overwrite an existing record. Then fsync the parent directory. A pre-publication failure leaves no committed partial step. A failure after link creation may report an error despite a committed record; retry the identical proposal and check the idempotent receipt. Actual power-loss durability depends on the storage system and is not exhaustively tested here.

Hashes detect accidental changes and inconsistent replay. They are not signatures and do not protect against someone rewriting the entire chain with recomputed hashes. The directory is trusted. Filesystem access policy and backup are host responsibilities.

## Query modes and answer provenance

**Base:** “What did this modeled reader understand after L3 from the original reading?” Use its saved state and allowed background/prefix. The inquiry log records questions and answers but is not automatically injected as evidence for future base queries.

**Dialogue:** “Starting from L3, let me explain this to the reader.” The original anchor stays frozen. Later messages and source additions are ordered events in that session. An explicitly resumed session sees them; a fresh session does not.

**Editorial:** An analyst interprets evidence at the anchor. `compare` can explicitly compare two saved positions and returns both scopes. v0.1 does not provide a general cross-run analytics engine or a dedicated comparison-log record. To record a comparison within an inquiry, anchor the editorial session at the later included position and cite earlier/current state IDs. Never present a later comparison as the earlier reader's knowledge.

Three common answers are deliberately different:

| Answer kind | What it means | Cost and persistence |
|---|---|---|
| `recorded` | Restates an actual saved observation or deterministic comparison | Retrieval needs no new simulation; log the answer when asked |
| `derived` | New interpretation from permitted saved state/prefix | May invoke an LLM; save as inquiry interpretation, not base history |
| `insufficient` | The requested information was not retained or is unsupported | Say what is missing; do not invent an earlier observation |
| `clarification` | Understanding depends on information supplied in this conversation | Dialogue/editorial only; source is a conversation event |

Example `exchange` (after a base session was opened at step 3):

```json
{
  "request_id": "question-001",
  "actor": "human",
  "question": "What explanation is still expected here?",
  "answer": "E1 asks when seen is updated and how it affects scheduling.",
  "answer_kind": "recorded",
  "claims": [{
    "text": "The scheduling role remains an open expectation at L3.",
    "basis": "recorded",
    "evidence": [{"kind": "state", "ref": "3"}]
  }],
  "added_sources": []
}
```

`request_id` supports retry idempotency within a session. A reused ID with different content conflicts. `expected_head_hash` is an optimistic concurrency check for a new exchange. Each complete question/answer exchange is one atomic event. This version has no separate “question pending” event, so an interrupted answer is not logged as a completed exchange.

### Conversation evidence

Document references remain bounded to the anchor. A later passage copied into the conversation is **new conversational evidence**, not a document reference that bypasses the prefix boundary. Session-local reference names are:

- `t1.question`: the first recorded question/clarification;
- `t1.source:c1`: a source introduced in that turn;
- `t1.answer`: a previous answer, usable only as a prior interpretation, not independent proof.

Current answers cannot cite themselves. The helper validates visibility, not whether a prior answer is being over-trusted. The skill supplies that semantic rule. There is no automatic semantic answer cache. Exact answer reuse must preserve run, anchor, mode, question scope, and—when relevant—session-history identity. Different reader profiles do not share a reader-state cache. In base mode, facts embedded in a leading question are requests/premises to examine, not new evidence about what the original reader knew.

## Schema and error policy

`artifact.schema.json` is the complete Draft 2020-12 structural contract. Small entry schemas select document, reader, config, delta, proposal, exchange, and request definitions. The runtime uses focused deterministic validators; JSON Schema checks are an additional optional development test, not a runtime dependency. Dynamic properties—source alignment, allowed reference visibility, replay, consecutive issue identities, concurrency—need code checks beyond JSON shape.

Expected codes include `INVALID`, `VISIBILITY`, `BUDGET`, `CONFLICT`, `NOT_COMPILED`, `COMPLETE`, `CORRUPT`, `READ_ERROR`, and `VERSION`. Non-finite data are rejected. On corruption, stop and report the affected artifact; do not silently regenerate it. On unavailable storage, do not claim persistence. Older schema versions must be rejected or explicitly migrated into new files; never reinterpret them in place.
