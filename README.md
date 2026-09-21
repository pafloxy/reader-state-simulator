# Reader State — portable agent skill

**Prepare once. Simulate a configured reader once. Ask the saved trace many questions.**

A portable agent skill with deterministic helpers, not a new writing application. A drafting agent uses it internally to inspect reader understanding and expectations; a human can later query the same artifact through that agent. Later clarification is remembered separately from the original reader trajectory.

## Status: 0.1.0 — 21 September 2026

This first public release joins the supplied ReaderSim document normalizer to the original trace/inquiry store. The six supplied Python source files and the store are preserved byte-for-byte; adapters, a local agent-facing command, tests, and documentation are added. **90 local tests pass.** The end-to-end example uses authored deltas, not a live model. A real isolated agent-host workflow has not been completed, so this release does not claim operationally verified host isolation. The project is available under the MIT License.

The product is `skills/reader-state/`. Everything else in this repository explains, demonstrates, or tests it. No UI, web service, model-provider framework, or database server is required.

## What gets reused

| Existing component | Role in this release |
|---|---|
| ReaderSim `normalization.py` | Ordered Markdown units and sentence addresses |
| ReaderSim `pipeline.py` | Existing normalization and text-prefix behavior, preserved |
| `reader_store.py` from RC1 | Validated cumulative state, replay, saved queries/dialogue |
| New `document_adapter.py` | Exact source projection and provenance bridge |
| New `reader_state.py` | Agent command/API joining preparation with the trace store |

`readersim compile` means **prepare a document**, not simulate a reader. `readersim query-at` means **return text through an address**, not return reader understanding. New `state_at` and `query_at` explicitly access the saved reader run.

## Try the actual bridge

Python 3.10+ and Linux/POSIX are required by the bundled code. Only Python 3.13.5 was executed for this release. Core runtime uses the standard library; JSON Schema development checks optionally use `jsonschema`.

```sh
python3 -B -m unittest discover -s tests -v
python3 -B examples/run_bridge_demo.py --root .reader-state-demo > demo-output.json
```

The example prepares `examples/document.md` with the original normalizer, commits five authored reader deltas, and retrieves the open question at L3 even after L5 resolves it. It appends an author clarification without changing L3. Running the demo again reuses its one matching run and adds a separate inquiry session; it does not regenerate the base trace.

Inspect the saved result from another process:

```sh
python3 - <<'PY'
import json, subprocess, sys
with open('demo-output.json', encoding='utf-8') as handle:
    run = json.load(handle)['run_id']
request = {'op': 'state_at', 'run_id': run, 'position': 'L3'}
subprocess.run([sys.executable, 'skills/reader-state/scripts/reader_state.py',
                '--root', '.reader-state-demo'],
               input=json.dumps(request), text=True, check=True)
PY
```

This proves the deterministic preparation/storage/query loop, not cognitive or live-agent fidelity.

## Install only the skill directory

For a host supporting repository-local `.agents/skills`, copy `skills/reader-state/` there. Avoid overwriting an existing same-name installation without reviewing differences. Example from a target project, with the release path set explicitly:

```sh
RELEASE=/absolute/path/to/reader-state-skill-0.1.0
mkdir -p .agents/skills
if test -e .agents/skills/reader-state; then
  printf '%s\n' 'Existing skill found: review before replacing.' >&2
else
  cp -R "$RELEASE/skills/reader-state" .agents/skills/reader-state
fi
```

For Codex, mention `$reader-state`; other hosts can load the same `SKILL.md` explicitly and bind script execution in their own way. Local discovery does not guarantee strict isolated inference, storage permissions, or automatic activation in every host. See `docs/SKILL-PACKAGING.md` for the verified documentation basis.

In ordinary writing work, a suitable instruction is:

> Use Reader State on this short passage for the specified audience. Reuse an exact matching saved run. Otherwise prepare the source, disclose the isolation mode, generate and save the reader trajectory, and answer from that trace. Save subsequent inquiries without changing the original history.

The main skill is 632 whitespace-delimited words, including frontmatter. Detailed references and schemas load only when needed; helper code is executed rather than pasted into the model context.

## Persistent artifact

```text
.reader-state/
  prepared/prep-<hash>.json
  run-<id>/
    run.json
    preparation.json
    trace/000001.json
    trace/000002.json
    inquiries/session-<id>/
      session.json
      events/000001.json
```

Preparation provenance is input bookkeeping, not a third kind of reader knowledge. The two semantic histories remain **base trace** and **inquiry history**. Neither manuscript edits nor author clarifications rewrite old snapshots.

## First-release scope

Native Markdown and the original native-Markdown normalized JSON are supported inputs. Block or sentence-level compilation is selected before the run. Structural units stay whole. A block trace cannot answer a finer sentence boundary; the helper returns an explicit error instead of leaking later information.

TeX/PDF conversion quality, rich linked artifacts, incremental suffix reuse, semantic proof checking, realistic forgetting, and human calibration are deferred. Older experimental formats are not silently coerced into the new schema. Runtime data includes private text; do not commit it publicly.

## Continue

`docs/ARCHITECTURE.md` explains the boundaries. `docs/MILESTONES.md` separates the released protocol alpha from its pending host-validation milestone. `TEST-REPORT.md` separates executed tests from unverified claims. `PROVENANCE.json` records unchanged source hashes. `LICENSE` contains the MIT License.
