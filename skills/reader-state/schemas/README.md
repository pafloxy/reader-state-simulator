# Schema entry points

`artifact.schema.json` is self-contained: its root accepts a run, committed step, session, or inquiry event. Its `$defs` also define inputs, proposals, queries, and values. The smaller `*.schema.json` files are local-file entry points; a validator using them must resolve relative file references against this directory. Do not fetch an imaginary schema server.

For an input without an external-reference resolver, load the complete schema and select its internal definition:

```python
import copy
import json
from jsonschema import Draft202012Validator

schema = json.load(open("artifact.schema.json", encoding="utf-8"))
selected = copy.deepcopy(schema)
selected.pop("oneOf")
selected["$ref"] = "#/$defs/document"  # reader, config, delta, etc. also work
Draft202012Validator(selected).validate(document_object)
```

This optional development dependency is not needed to run the store. The runtime helper additionally checks properties JSON shape cannot establish: exact source alignment, allowed reference visibility, issue lifecycle, sequential hash chains, and deterministic replay. Neither layer establishes semantic entailment, real human-reader fidelity, or host isolation.

## v0.1 bridge schemas

`preparation.schema.json` describes an unstamped prepared input; persisted preparation files add a `hash`. `preparation-binding.schema.json` describes the run's stamped binding with an embedded prepared input. `bridge-request.schema.json` covers additional facade operations. Base operations still use `request.schema.json`. Resolve relative schema references from this directory; the optional tests register all schemas locally and make no network requests.

These are structural schemas, not evidence that a rendered source was reconstructed faithfully or that a host isolated its reader model. Semantic visibility and transition checks remain in the helper and host.
