#!/usr/bin/env python3
"""Agent-facing binding: ReaderSim preparation + durable reader/inquiry store.

Use --root PROJECT/.reader-state and one JSON request on stdin or --request FILE.
No LLM calls. Model inference and genuine isolation are supplied by the host.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from document_adapter import prepare_document, validate_preparation
from readersim.normalization import canonicalize_position
from reader_store import (TraceStore, StoreError, require, read_json, atomic_new,
                          stamped, check_hash, digest)

PREP_ID = re.compile(r"prep-[0-9a-f]{64}\Z")


class ReaderSkillStore(TraceStore):
    def prepare(self, source, document_id, granularity="block", input_format="markdown"):
        prepared = prepare_document(source, document_id, granularity, input_format)
        pid = "prep-" + digest(prepared)
        directory = self.root / "prepared"
        directory.mkdir(exist_ok=True)
        path = directory / (pid + ".json")
        try:
            atomic_new(path, stamped(prepared))
        except StoreError as exc:
            if exc.code != "CONFLICT":
                raise
            old = self._prepared(pid)
            require(old == prepared, "existing preparation differs", "CORRUPT")
        return {"preparation_id": pid, "path": str(path),
                "document_digest": prepared["document_digest"],
                "revision": prepared["document"]["revision"],
                "unit_count": len(prepared["document"]["units"]),
                "warnings": prepared["provenance"]["warnings"],
                "reader_simulation": "not_run"}

    def _prepared(self, preparation_id):
        require(isinstance(preparation_id, str) and bool(PREP_ID.fullmatch(preparation_id)),
                "invalid preparation ID")
        p = read_json(self.root / "prepared" / (preparation_id + ".json"))
        check_hash(p)
        raw = {k: v for k, v in p.items() if k != "hash"}
        validate_preparation(raw)
        require(preparation_id == "prep-" + digest(raw), "preparation ID mismatch", "CORRUPT")
        return raw

    def inspect_prepared(self, preparation_id):
        """For source review by the author/orchestrator; NOT for the reader worker."""
        return self._prepared(preparation_id)

    def create_prepared(self, preparation_id, reader, config, reviewed=False, reuse=True):
        require(reviewed is True, "review reader-visible source representation before creating a run", "REVIEW_REQUIRED")
        require(type(reuse) is bool, "reuse must be boolean")
        p = self._prepared(preparation_id)
        key = digest({"document": p["document"], "reader": reader, "config": config})
        candidates = self.list_runs(key) if reuse else []
        # Only reuse a run with an intact preparation binding to this same preparation.
        matches = []
        for c in candidates:
            binding = self.path(c["run_id"]) / "preparation.json"
            if binding.is_file():
                b = self.preparation_for_run(c["run_id"])
                if b["preparation_id"] == preparation_id:
                    matches.append(c)
        require(len(matches) <= 1, "multiple matching samples; choose a run_id explicitly", "AMBIGUOUS_RUN")
        if matches:
            chosen = matches[0]
            self.verify(chosen["run_id"])
            return {"run_id": chosen["run_id"], "input_digest": key,
                    "path": str(self.path(chosen["run_id"])), "reused": True}
        result = self.create(p["document"], reader, config)
        m = self.manifest(result["run_id"])
        atomic_new(self.path(result["run_id"]) / "preparation.json",
                   stamped({"schema_version": "reader-state.preparation-binding.v1",
                            "run_id": result["run_id"], "manifest_hash": m["hash"],
                            "preparation_id": preparation_id, "preparation": p}))
        # A process failure between create and this binding can leave an incomplete
        # preparation binding. Such a run is never auto-reused; inspect/quarantine it.
        return dict(result, reused=False)

    def preparation_for_run(self, run_id):
        b = read_json(self.path(run_id) / "preparation.json")
        check_hash(b)
        m = self.manifest(run_id)
        require(b.get("schema_version") == "reader-state.preparation-binding.v1"
                and b.get("run_id") == run_id and b.get("manifest_hash") == m["hash"],
                "preparation binding mismatch", "CORRUPT")
        validate_preparation(b["preparation"])
        require(b["preparation"]["document"] == m["document"], "prepared source differs from run", "CORRUPT")
        require(b["preparation_id"] == "prep-" + digest(b["preparation"]),
                "preparation content ID mismatch", "CORRUPT")
        return b

    def resolve_at(self, run_id, position):
        if position == "L0":
            return {"step": 0, "requested_position": position, "resolved_position": "L0", "resolution": "baseline"}
        try:
            canonical = canonicalize_position(position)
        except ValueError as exc:
            raise StoreError("INVALID_POSITION", str(exc)) from exc
        units = self.manifest(run_id)["document"]["units"]
        for step, u in enumerate(units, 1):
            if u["position"] == canonical:
                return {"step": step, "requested_position": position, "resolved_position": canonical, "resolution": "exact"}
        # End-of-block aliases the last child only in a verified sentence projection.
        binding = self.path(run_id) / "preparation.json"
        if "." not in canonical and binding.is_file():
            b = self.preparation_for_run(run_id)
            policy = b["preparation"]["provenance"]["projection_policy"]
            if policy == "readersim-sentence-v1":
                candidates = [(i, u) for i, u in enumerate(units, 1) if u["position"].startswith(canonical + ".")]
                if candidates:
                    step, u = candidates[-1]
                    return {"step": step, "requested_position": position,
                            "resolved_position": u["position"], "resolution": "end-of-block"}
        raise StoreError("BOUNDARY_MISSING", "this run has no snapshot boundary at " + canonical +
                         "; never relabel a block snapshot as an earlier sentence")

    def state_at(self, run_id, position, registers=None):
        resolved = self.resolve_at(run_id, position)
        return dict(self.get(run_id, resolved["step"], registers), address_resolution=resolved)

    def query_at(self, run_id, position, session_id=None):
        resolved = self.resolve_at(run_id, position)
        return dict(self.query_context(run_id, resolved["step"], session_id), address_resolution=resolved)

    def verify(self, run_id):
        result = super().verify(run_id)
        binding = self.path(run_id) / "preparation.json"
        if binding.is_file():
            self.preparation_for_run(run_id)
            result["preparation_binding"] = "verified"
        else:
            result["preparation_binding"] = "absent: hand-authored/legacy run or interrupted preparation; not auto-reusable"
        return result

    def dispatch(self, request):
        require(isinstance(request, dict), "request must be an object")
        op = request.get("op")
        extra = {"prepare": self.prepare, "inspect_prepared": self.inspect_prepared,
                 "create_prepared": self.create_prepared, "resolve_at": self.resolve_at,
                 "state_at": self.state_at, "query_at": self.query_at,
                 "preparation_for_run": self.preparation_for_run}
        if isinstance(op, str) and op in extra:
            try:
                return extra[op](**{k: v for k, v in request.items() if k != "op"})
            except TypeError as exc:
                raise StoreError("INVALID", "invalid arguments for " + op + ": " + str(exc)) from exc
        return super().dispatch(request)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--request", default="-")
    args = parser.parse_args()
    try:
        request = json.load(sys.stdin) if args.request == "-" else read_json(args.request)
        result = ReaderSkillStore(args.root).dispatch(request)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False))
    except (StoreError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": {"code": getattr(exc, "code", "IO_OR_INPUT"), "message": str(exc)}}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
