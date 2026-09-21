# Changelog

## 0.1.0 — 21 September 2026

Reconciled the uploaded ReaderSim source subset with the skill-first design. Added a source-provenance adapter and an agent-facing local command. Preserved all six supplied Python source files and the RC1 state store unchanged. Added preparation persistence/bindings, unique matching-run reuse, label resolution, state/query operations, sentence-boundary safeguards, and bridge schemas. Refused unsupported converted/rich artifacts instead of silently degrading them. Added 41 deterministic/schema/packaging tests to the retained 49. Updated the compact skill and narrowed release milestones.

Published the allowlisted skill package under the MIT License. No model provider was invoked and no global skill installation was performed. Real host isolation and human-reader fidelity remain explicitly unverified.
