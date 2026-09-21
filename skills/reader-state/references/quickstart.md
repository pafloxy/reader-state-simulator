# Agent quickstart — v0.1

Resolve the installed skill's absolute directory as `SKILL_ROOT`. Run its helper from any project directory:

```sh
python3 "$SKILL_ROOT/scripts/reader_state.py" --root .reader-state --request request.json
```

The same command accepts a JSON object on stdin. Success returns `{"ok": true, "result": ...}`. Input/storage errors return `{"ok": false, "error": {"code": ..., "message": ...}}` with exit code 2. The included Python API is `ReaderSkillStore(root)`.

## 1. Prepare a short passage

```json
{"op":"prepare","source":"draft.md","document_id":"article-introduction","granularity":"block"}
```

This saves a preparation, returns its `preparation_id`, path, revision, count, and warnings, and makes zero model calls. Use `input_format: "legacy-json"` only for the supported native-Markdown normalized artifact.

An author/orchestrator may review the preparation via:

```json
{"op":"inspect_prepared","preparation_id":"PREPARATION_ID_FROM_RESULT"}
```

That returns the whole prepared input. Do **not** send it to the isolated reader. The public demo's reader and config files illustrate exact input shapes; do not use its fixture model metadata for a real run.

## 2. Create or reuse the run

```json
{
  "op":"create_prepared",
  "preparation_id":"PREPARATION_ID_FROM_RESULT",
  "reviewed":true,
  "reader":{
    "reader_id":"cs-undergraduate",
    "persona":"Knows sets and directed graphs; graph traversal algorithms are not assumed.",
    "strictness":1,
    "background":[],
    "initial_knowledge":{}
  },
  "config":{
    "model":"RECORD_ACTUAL_HOST_MODEL",
    "prompt_version":"reader-state-0.1",
    "isolation":"instruction-only",
    "context_policy":"full-prefix-v1",
    "max_units":50
  }
}
```

This example deliberately declares `instruction-only`; upgrade it to `isolated` only after verifying the actual host's context/tool controls. For substantive simulations, specify background assumptions/excerpts and initial knowledge as appropriate, rather than inventing expertise from a short persona label.

The result includes `run_id` and `reused`. A matching run is reused, including a partial frontier. Use `list` to inspect matching runs, or an explicit existing `run_id`. Do not silently pick a latest run. `reuse:false` requests resampling.

## 3. Advance

```json
{"op":"context","run_id":"RUN_ID_FROM_RESULT"}
```

Give the reader inference only `result.context` plus the fixed instructions and delta schema. Keep ticket hashes in the orchestrator. Return a delta; do not ask the model to reconstruct previous state or choose filesystem paths.

```json
{
  "op":"commit",
  "run_id":"RUN_ID_FROM_RESULT",
  "proposal":{
    "step":1,
    "expected_parent_hash":"COPY_TICKET_VALUE",
    "context_hash":"COPY_TICKET_VALUE",
    "delta":{"updates":[],"issue_events":[]}
  }
}
```

An empty delta is valid only when the model found no change. It is not a substitute for inference. Iterate until the requested frontier, completion, or an agreed budget. The helper has no built-in LLM adapter or cost meter.

## 4. Ask from the saved artifact

```json
{"op":"state_at","run_id":"RUN_ID_FROM_RESULT","position":"L3","registers":["expectations","understanding"]}
```

`state_at` returns recorded state and issues. It performs zero model calls. Omit `registers` for all registers. `query_at` returns the bounded prefix and selected snapshot when an interpretation is needed. It still performs no model call itself.

```json
{"op":"query_at","run_id":"RUN_ID_FROM_RESULT","position":"L3"}
```

`resolve_at` maps a label to a step without claiming that the step has been compiled. `state_at`/`query_at` reject uncompiled steps. The old `readersim query-at` retrieves a document prefix only, not a reader state.

## 5. Record an inquiry

Open a session using the numeric step returned by `state_at` or `resolve_at`:

```json
{"op":"open_session","run_id":"RUN_ID_FROM_RESULT","step":3,"mode":"base"}
```

Then record an actual exchange:

```json
{
  "op":"append_exchange",
  "run_id":"RUN_ID_FROM_RESULT",
  "session_id":"SESSION_ID_FROM_RESULT",
  "expected_head_hash":"HEAD_HASH_FROM_RESULT",
  "exchange":{
    "request_id":"question-001",
    "actor":"human",
    "question":"What explanation is the reader waiting for here?",
    "answer":"WRITE_THE_ACTUAL_SUPPORTED_ANSWER",
    "answer_kind":"recorded",
    "claims":[],
    "added_sources":[]
  }
}
```

Use `actor:agent` for a self-diagnostic inquiry. Populate supported claims/evidence for substantive answers. Use `derived` for new interpretations and `insufficient` when the record does not support an answer. `dialogue` permits explicitly attributed author clarification; `editorial` identifies analyst interpretation. Only an explicitly resumed dialogue/editorial session contributes inquiry history to `query_at`. See the existing protocol for exact evidence shapes.

## 6. Verify and report

```json
{"op":"verify","run_id":"RUN_ID_FROM_RESULT"}
```

Report the run/profile/revision, stored frontier, relevant findings, and remaining limits. `verify` checks structure, references, hashes, replay, and available preparation binding—not actual human behavior or model isolation.
