"""Compile source documents and construct strict reader-visible prefixes.

This module implements normalization only. It labels the resulting artifact so
callers cannot confuse deterministic document preparation with a simulated
reader-state trace.

Usage example::

    artifact_path = compile_document(Path("draft.md"))
    prefix = build_prefix(load_artifact(artifact_path), "L3.1")
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .conversion import ConversionError, source_to_markdown
from .normalization import canonicalize_position, normalize_markdown


class ArtifactError(RuntimeError):
    """Report an invalid artifact, output, or requested position."""


def compile_document(
    source_path: Path,
    output_path: Path | None = None,
    *,
    indent: int = 2,
) -> Path:
    """Convert and normalize a source file into the V0 JSON artifact.

    Args:
        source_path: Markdown or a MarkItDown-supported source file.
        output_path: Optional output override. By default, ``draft.md`` or
            ``draft.pdf`` becomes ``draft.reader-state-simulation.json``.
        indent: JSON indentation level.

    Returns:
        Path to the written artifact.

    Example:
        ``compile_document(Path("draft.md"), Path("trial.json"))``
    """

    source_path = source_path.expanduser().resolve()
    try:
        source_bytes = source_path.read_bytes()
    except OSError as error:
        raise ArtifactError(f"cannot read input file: {error}") from error
    try:
        markdown, conversion = source_to_markdown(source_path)
    except ConversionError as error:
        raise ArtifactError(str(error)) from error

    document = normalize_markdown(markdown)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    normalized_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    artifact = {
        "schema_version": "readersim.normalized-document.v0.2",
        "artifact_kind": "normalized_document",
        "pipeline_status": "normalization_complete",
        "reader_simulation": {
            "status": "not_run",
            "reason": "This artifact contains deterministic document preparation only.",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "name": source_path.name,
            "path": str(source_path),
            "byte_length": len(source_bytes),
            "sha256": source_hash,
            "document_revision_id": f"sha256:{source_hash}",
        },
        "conversion": conversion,
        "normalization": {
            "normalized_sha256": normalized_hash,
            "unit_count": len(document["units"]),
            "sentence_count": sum(
                len(unit["sentences"]) for unit in document["units"]
            ),
            "offset_unit": "unicode_code_point",
            "parser": "readersim-stdlib-markdown-v0.2",
            "warnings": _normalization_warnings(document),
        },
        "document": document,
    }

    destination = (
        output_path.expanduser().resolve()
        if output_path is not None
        else source_path.with_name(
            f"{source_path.stem}.reader-state-simulation.json"
        )
    )
    if destination == source_path:
        raise ArtifactError("output path must not overwrite the source document")
    if destination.exists() and destination.is_dir():
        raise ArtifactError(f"output path is a directory: {destination}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=indent) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise ArtifactError(f"cannot write output artifact: {error}") from error
    return destination


def load_artifact(artifact_path: Path) -> dict[str, Any]:
    """Load and minimally validate a normalized-document JSON artifact.

    Example:
        ``artifact = load_artifact(Path("draft.reader-state-simulation.json"))``
    """

    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ArtifactError(f"artifact does not exist: {artifact_path}") from error
    except (OSError, UnicodeError) as error:
        raise ArtifactError(f"cannot read artifact: {error}") from error
    except json.JSONDecodeError as error:
        raise ArtifactError(f"artifact is not valid JSON: {error}") from error

    if not isinstance(artifact, dict):
        raise ArtifactError("artifact root must be a JSON object")
    if artifact.get("artifact_kind") != "normalized_document":
        raise ArtifactError("artifact is not a readersim normalized_document")
    if not isinstance(artifact.get("document", {}).get("units"), list):
        raise ArtifactError("artifact document.units must be a list")
    return artifact


def build_prefix(artifact: dict[str, Any], position: str) -> dict[str, Any]:
    """Construct a suffix-free reader-visible bundle after one position.

    For ``L3.1``, earlier units are included in full and the current unit is
    truncated at the end of its first sentence. No full-document indexes,
    future unit count, normalized source, or suffix records are copied.

    Example:
        ``prefix = build_prefix(artifact, "L3.1")``
    """

    try:
        canonical = canonicalize_position(position)
    except ValueError as error:
        raise ArtifactError(str(error)) from error

    units = artifact["document"]["units"]
    target_unit_number, target_sentence_number = _parse_canonical_position(canonical)
    if target_unit_number > len(units):
        raise ArtifactError(f"position is not stored in this artifact: {canonical}")

    target_unit = units[target_unit_number - 1]
    if target_sentence_number is not None:
        sentences = target_unit.get("sentences", [])
        if target_sentence_number > len(sentences):
            raise ArtifactError(f"position is not stored in this artifact: {canonical}")
        target_end = sentences[target_sentence_number - 1]["source_span"]["end"]
    else:
        target_end = target_unit["source_span"]["end"]

    visible_units: list[dict[str, Any]] = []
    for unit in units[:target_unit_number]:
        if unit["reading_order"] < target_unit_number:
            visible_units.append(_copy_visible_unit(unit, None))
        else:
            visible_units.append(_copy_visible_unit(unit, target_end))

    source = artifact["source"]
    return {
        "schema_version": "readersim.reader-visible-prefix.v0.2",
        "artifact_kind": "reader_visible_prefix",
        "source_revision": {
            "name": source["name"],
            "document_revision_id": source["document_revision_id"],
        },
        "requested_position": position,
        "resolved_position": canonical,
        "boundary_semantics": "after",
        "coverage": {
            "from": visible_units[0]["label"] if visible_units else None,
            "through": canonical,
        },
        "units": visible_units,
        "isolation": {
            "suffix_included": False,
            "whole_document_indexes_included": False,
            "whole_document_graph_included": False,
            "reader_simulation_performed": False,
        },
    }


def write_json_result(
    result: dict[str, Any], output_path: Path | None, *, indent: int = 2
) -> str | None:
    """Serialize a query result to a file or return it for standard output.

    Example:
        ``stdout_text = write_json_result({"ok": True}, None)``
    """

    payload = json.dumps(result, ensure_ascii=False, indent=indent) + "\n"
    if output_path is None:
        return payload
    try:
        output_path.expanduser().resolve().write_text(payload, encoding="utf-8")
    except OSError as error:
        raise ArtifactError(f"cannot write query result: {error}") from error
    return None


def _parse_canonical_position(position: str) -> tuple[int, int | None]:
    """Parse a position already validated by ``canonicalize_position``.

    Example:
        ``_parse_canonical_position("L3.2") == (3, 2)``
    """

    unit_text, separator, sentence_text = position[1:].partition(".")
    return int(unit_text), int(sentence_text) if separator else None


def _normalization_warnings(document: dict[str, Any]) -> list[str]:
    """Report structures that may make address granularity misleading.

    Very long prose blocks commonly indicate that a source converter preserved
    visual lines but lost paragraph breaks. The threshold is a diagnostic, not
    a claim that a shorter unit is semantically correct.

    Example:
        ``_normalization_warnings(normalize_markdown("Short.")) == []``
    """

    long_units = [
        unit["label"]
        for unit in document["units"]
        if unit["kind"] in {"paragraph", "blockquote", "list_item"}
        and len(unit["text"]) > 3000
    ]
    if not long_units:
        return []
    shown = ", ".join(long_units[:10])
    suffix = " ..." if len(long_units) > 10 else ""
    return [
        "Unusually long prose units detected ("
        f"{shown}{suffix}); source conversion may not have preserved paragraph "
        "boundaries. Sentence addresses remain available, but inspect the "
        "normalized Markdown before simulation."
    ]


def _copy_visible_unit(unit: dict[str, Any], target_end: int | None) -> dict[str, Any]:
    """Copy one unit without retaining content after an optional source offset.

    Example:
        ``_copy_visible_unit(unit, None)`` copies a fully visible prior unit.
    """

    visible_sentences = [
        {
            "label": sentence["label"],
            "text": sentence["text"],
        }
        for sentence in unit.get("sentences", [])
        if target_end is None or sentence["source_span"]["end"] <= target_end
    ]
    if target_end is None:
        text = unit["text"]
    else:
        unit_start = unit["source_span"]["start"]
        text = unit["text"][: max(0, target_end - unit_start)].rstrip()
    return {
        "label": unit["label"],
        "reading_order": unit["reading_order"],
        "kind": unit["kind"],
        "text": text,
        "sentences": visible_sentences,
    }
