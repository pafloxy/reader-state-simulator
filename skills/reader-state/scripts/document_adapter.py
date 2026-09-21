"""Bridge the supplied ReaderSim normalizer to the Reader State trace contract.

Standard library only, Python 3.10+. No model calls, converters, or source writes.
Only native Markdown and native-Markdown normalized-document.v0.2 are accepted.
A preparation is a private audit object, NOT a reader-worker context.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from readersim.normalization import normalize_markdown, validate_normalized_document
from reader_store import StoreError, require, identifier, digest, encode

SCHEMA = "reader-state.preparation.v1"
LEGACY_SCHEMA = "readersim.normalized-document.v0.2"
MAX_SOURCE_BYTES = 5 * 1024 * 1024
KINDS = {"paragraph": "prose", "list_item": "prose", "blockquote": "prose",
         "heading": "heading", "math_block": "math", "code_block": "code",
         "table": "table", "html_block": "opaque", "thematic_break": "opaque"}
HEX = re.compile(r"[0-9a-f]{64}\Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(raw: bytes) -> dict[str, Any]:
    def no_constant(value):
        raise ValueError("non-finite number: " + value)
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError("duplicate JSON key: " + k)
            out[k] = v
        return out
    try:
        value = json.loads(raw.decode("utf-8"), parse_constant=no_constant,
                           object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise StoreError("INVALID_SOURCE", str(exc)) from exc
    require(isinstance(value, dict), "source artifact must be an object")
    return value


def _validate_legacy(a: dict[str, Any]) -> tuple[dict[str, Any], str, str, list[str]]:
    """Fail closed on unreviewed converters and richer experimental formats."""
    require(a.get("schema_version") == LEGACY_SCHEMA and
            a.get("artifact_kind") == "normalized_document",
            "expected native ReaderSim normalized-document.v0.2", "UNSUPPORTED_FORMAT")
    require(set(a) <= {"schema_version", "artifact_kind", "pipeline_status",
                      "reader_simulation", "created_at", "source", "conversion",
                      "normalization", "document"},
            "extended/linked artifact package needs its own audited adapter", "UNSUPPORTED_FORMAT")
    try:
        require(a["reader_simulation"]["status"] == "not_run",
                "do not import a simulation as a normalized input", "UNSUPPORTED_FORMAT")
        require(a["conversion"]["converter"] == "native-markdown",
                "converted TeX/PDF is not an alpha input; review/export clean Markdown first",
                "UNSUPPORTED_FORMAT")
        d = a["document"]
        require(set(d) == {"front_matter", "normalized_markdown", "addressing", "units", "indexes"},
                "extended document fields must not be silently discarded", "UNSUPPORTED_FORMAT")
        require(isinstance(d["normalized_markdown"], str), "normalized text must be a string")
        require(a["normalization"]["normalized_sha256"] == sha(d["normalized_markdown"].encode("utf-8")),
                "normalized Markdown hash mismatch", "CORRUPT")
        h = a["source"]["sha256"]
        require(isinstance(h, str) and bool(HEX.fullmatch(h)), "bad recorded source hash")
        name = a["source"]["name"]
        require(isinstance(name, str) and name and "/" not in name and "\\" not in name,
                "source name must not be a path")
        require(a["source"]["document_revision_id"] == "sha256:" + h,
                "source revision/hash disagree", "CORRUPT")
        fm = d["front_matter"]
        if fm is not None:
            # Re-parse only to validate the excluded metadata boundary; never accept
            # a tampered metadata span that hides arbitrary body paragraphs.
            expected = normalize_markdown(d["normalized_markdown"])["front_matter"]
            require(fm == expected and fm["reader_visible"] is False,
                    "frontmatter boundary does not match the pinned parser", "CORRUPT")
        for u in d["units"]:
            require(set(u) == {"id", "label", "reading_order", "kind", "text", "source_span", "sentences"},
                    "extended unit fields need an explicit adapter", "UNSUPPORTED_FORMAT")
            require(u["kind"] in KINDS, "unsupported unit kind", "UNSUPPORTED_FORMAT")
            for s in u["sentences"]:
                require(set(s) == {"id", "label", "sentence_order", "text", "source_span"},
                        "extended sentence fields need an explicit adapter", "UNSUPPORTED_FORMAT")
        validate_normalized_document(d)
        warnings = a["conversion"].get("warnings", []) + a["normalization"].get("warnings", [])
        require(isinstance(warnings, list) and all(isinstance(x, str) for x in warnings),
                "warnings must be strings")
        warnings = warnings + ["Original source bytes are not present: the input artifact's source hash is retained, not independently verified."]
        return d, h, name, warnings
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise StoreError("INVALID_SOURCE", "inconsistent legacy artifact: " + str(exc)) from exc


def prepare_document(source: str | Path, document_id: str,
                     granularity: str = "block", input_format: str = "markdown") -> dict[str, Any]:
    identifier(document_id)
    require(granularity in ("block", "sentence"), "granularity must be block or sentence")
    require(input_format in ("markdown", "legacy-json"), "unknown input format")
    p = Path(source).expanduser()
    require(p.is_file(), "source file is missing", "NOT_FOUND")
    require(p.stat().st_size <= MAX_SOURCE_BYTES, "source exceeds 5 MiB alpha limit", "BUDGET")
    raw = p.read_bytes()
    require(len(raw) <= MAX_SOURCE_BYTES, "source exceeds 5 MiB alpha limit", "BUDGET")
    warnings = []
    if input_format == "markdown":
        require(p.suffix.lower() in (".md", ".markdown"),
                "alpha accepts .md/.markdown; no automatic TeX/PDF conversion", "UNSUPPORTED_FORMAT")
        try:
            normalized = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeError as exc:
            raise StoreError("INVALID_SOURCE", "Markdown must be UTF-8") from exc
        d = normalize_markdown(normalized)
        source_hash, source_name = sha(raw), p.name
        if any(len(u["text"]) > 3000 and u["kind"] in ("paragraph", "blockquote", "list_item") for u in d["units"]):
            warnings.append("Long prose unit: inspect paragraph boundaries before committing a run.")
    else:
        d, source_hash, source_name, warnings = _validate_legacy(_json(raw))
        normalized = d["normalized_markdown"]
    fm = d["front_matter"]
    body_start = fm["source_span"]["end"] if fm is not None else 0
    reader_text = normalized[body_start:]
    units, source_map = [], []
    if fm is not None:
        warnings.append("YAML frontmatter is excluded from reader text; original normalized offsets are retained in the private source map.")
    if any(u["kind"] in ("html_block", "table", "math_block", "code_block") for u in d["units"]):
        warnings.append("Structural blocks remain literal Markdown/source representations, not rendered visual interpretations.")
    if re.search(r"!\[|!\[\[|\[\[", reader_text):
        warnings.append("Links/embeds are retained as text only; no linked files or images were fetched or read.")
    previous_end = 0
    for u in d["units"]:
        children = u["sentences"] if granularity == "sentence" and u["sentences"] else [u]
        for child in children:
            span = child["source_span"]
            start, end = span["start"] - body_start, span["end"] - body_start
            require(type(start) is int and type(end) is int and previous_end <= start < end <= len(reader_text),
                    "invalid/overlapping projected spans", "INVALID_SOURCE")
            require(not reader_text[previous_end:start].strip(),
                    "unit map omits reader-visible content", "INVALID_SOURCE")
            require(reader_text[start:end] == child["text"], "source-map/text mismatch", "INVALID_SOURCE")
            identifier(child["id"])
            units.append({"unit_id": child["id"], "position": child["label"],
                          "text": child["text"], "start": start, "end": end,
                          "kind": KINDS[u["kind"]]})
            source_map.append({"unit_id": child["id"], "position": child["label"],
                               "legacy_parent": u["label"], "legacy_kind": u["kind"],
                               "normalized_start": span["start"], "normalized_end": span["end"]})
            previous_end = end
    require(bool(units), "no reader-visible units", "INVALID_SOURCE")
    require(not reader_text[previous_end:].strip(), "unit map omits source suffix", "INVALID_SOURCE")
    require(len({u["unit_id"] for u in units}) == len(units), "duplicate unit IDs", "INVALID_SOURCE")
    require(len({u["position"] for u in units}) == len(units), "duplicate positions", "INVALID_SOURCE")
    doc = {"document_id": document_id, "revision": "sha256:" + source_hash,
           "granularity": "explicit", "source_text": reader_text, "units": units}
    return {"schema_version": SCHEMA, "document": doc,
            "document_digest": digest(doc),
            "provenance": {"input_format": input_format, "input_bytes_sha256": sha(raw),
                           "original_source_name": source_name, "original_source_sha256": source_hash,
                           "normalized_sha256": sha(normalized.encode("utf-8")),
                           "normalizer_schema": LEGACY_SCHEMA,
                           "projection_policy": "readersim-" + granularity + "-v1",
                           "offset_unit": "unicode_code_point",
                           "body_start": body_start, "frontmatter_excluded": fm is not None,
                           "source_map": source_map, "warnings": warnings}}


def validate_preparation(p: dict[str, Any]) -> None:
    require(isinstance(p, dict) and p.get("schema_version") == SCHEMA,
            "unknown preparation schema", "VERSION")
    require(p.get("document_digest") == digest(p["document"]), "preparation/document mismatch", "CORRUPT")
    encode(p)
