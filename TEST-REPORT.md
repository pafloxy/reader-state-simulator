# Verification report — 21 September 2026

## Environment and commands

Executed in the available Linux container with CPython 3.13.5. Python 3.10+ is the declared code requirement, but 3.10/3.11/3.12 and the user's actual Ubuntu environment were not independently executed here. No model provider or network converter was invoked.

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python -B -S -m unittest discover -s tests -v
python -B examples/run_bridge_demo.py --root <temporary-artifact-directory>
```

## Results

| Check | Result |
|---|---|
| Re-run of the unchanged RC1 suite before integration | 49 passed |
| Combined release suite with optional JSON Schema dependencies available | 90 passed, 0 skipped |
| Combined suite with site-packages disabled (`-S`) | 82 passed, 8 optional schema checks skipped |
| Source equality against actually extracted upload | All six legacy `.py` modules byte-identical |
| Store equality against actually extracted RC1 | `reader_store.py` byte-identical |
| Independent skill-directory copy | Helper executes outside the release repo, without custom PYTHONPATH |
| Authored bridge demonstration | Five units committed, original L3 issue retained after L5 resolution, later clarification separate |
| Main skill size | 632 whitespace-delimited words including frontmatter; not a token estimate |
| Local Markdown reference paths | No broken links found |
| Skill frontmatter and optional host metadata | Parsed successfully as YAML |
| Release JSON | All files parsed successfully |

Fresh release output: `verification/release-test-run.txt`, `verification/release-stdlib-test-run.txt`. The original candidate outputs remain at `verification/test-run.txt` and `verification/stdlib-test-run.txt`. Source hashes: `PROVENANCE.json`. `examples/bridge-artifacts/` and `examples/bridge-demo-result.json` contain the synthetic saved bridge run; `examples/sample-artifacts/` retains the compatibility fixture.

## What the 41 added tests cover

Source/label reuse; YAML exclusion; Unicode-codepoint spans and raw-byte hashes; newline normalization; sentence and structural boundaries; no future-sentence payload content; rejecting a sentence query on a block trace; canonical dotted/hyphenated aliases; explicit block-end resolution; missing/uncompiled boundaries; idempotent preparation; required representation review; exact-match reuse; changed source/reader identity; ambiguous resamples; native legacy import; wrong hashes; refusing rich/converted artifacts; source preservation; tampered preparations and bindings; fresh-process retrieval; end-to-end inquiry separation; legacy prefix behavior; standalone skill copying; empty input; path-like invalid positions; no original absolute paths in preparation content; text-only embeds; incomplete input maps; baseline state; instruction-as-data payload policy; legacy module CLI preservation; source hash checks; compact skill links; and bridge schema conformance.

## Important limitations

The original project's eight-test suite was not supplied and was not rerun. The 174 manuscript experiment snapshots and their reports were not supplied; their historical results are supported only by uploaded logs in this pass.

No live agent/model generated semantic deltas, no strict host isolation was demonstrated, and no human-reader prediction or improved-writing claim was tested. Authored fixtures are labeled as fixtures. A test of the helper's source-data policy is not a test of model prompt-injection resistance. Hashes and replay checks are not proofs of semantic entailment or cryptographic authentication against a hostile writer.

The new preparation binding is not a multi-file transaction; interrupted creation can leave a base run without its preparation binding. This is reported and excluded from automatic prepared-run reuse. Concurrent distributed operation, hostile workspace access, realistic memory, large-manuscript performance, and rich rendered-document fidelity are outside tested claims.

No public repository was created or modified; no skill was installed on the user's machine. A real host smoke test, license choice, and public-content review remain release gates.
