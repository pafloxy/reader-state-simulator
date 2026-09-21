"""Normalize Markdown into ordered, addressable document units.

The parser is intentionally conservative and dependency-free. It preserves
exact Markdown slices, assigns numeric reading order, and splits sentences only
inside prose-like blocks.

Usage example::

    document = normalize_markdown("# Title\n\nOne sentence. Another one!")
    assert document["units"][1]["sentences"][0]["label"] == "L2.1"
"""

from __future__ import annotations

import re
from typing import Any


_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}(?:[ \t]+|$)")
_LIST_RE = re.compile(r"^[ \t]{0,3}(?:[-+*]|\d+[.)])[ \t]+")
_THEMATIC_RE = re.compile(
    r"^[ \t]{0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$"
)
_TABLE_DELIMITER_RE = re.compile(
    r"^[ \t]*\|?[ \t]*:?-{3,}:?[ \t]*(?:\|[ \t]*:?-{3,}:?[ \t]*)+\|?[ \t]*$"
)
_ABBREVIATIONS = {
    "e.g.",
    "i.e.",
    "etc.",
    "fig.",
    "eq.",
    "sec.",
    "dr.",
    "mr.",
    "mrs.",
    "ms.",
    "prof.",
    "vs.",
}


def normalize_markdown(markdown: str) -> dict[str, Any]:
    """Convert Markdown text into ordered typed units and sentence children.

    Front matter is preserved as metadata and excluded from the reader-visible
    sequence. Each remaining top-level block receives ``L<n>``; prose-like
    blocks additionally receive sentence labels ``L<n>.<m>``.

    Example:
        ``normalize_markdown("Hello. Next.")["units"][0]["label"] == "L1"``
    """

    front_matter, content_start = _extract_front_matter(markdown)
    lines = markdown.splitlines(keepends=True)
    offsets = _line_offsets(lines)
    start_line = _line_index_at_offset(offsets, content_start)
    units: list[dict[str, Any]] = []
    line_index = start_line

    while line_index < len(lines):
        if not lines[line_index].strip():
            line_index += 1
            continue

        block_start_line = line_index
        kind, block_end_line = _consume_block(lines, line_index)
        line_index = block_end_line
        start = offsets[block_start_line]
        end = offsets[block_end_line] if block_end_line < len(offsets) else len(markdown)
        end = _trim_line_endings(markdown, start, end)
        if end <= start:
            continue

        label = f"L{len(units) + 1}"
        text = markdown[start:end]
        sentences = []
        if kind in {"paragraph", "blockquote", "list_item"}:
            for sentence_order, (sentence_start, sentence_end) in enumerate(
                sentence_spans(text), start=1
            ):
                absolute_start = start + sentence_start
                absolute_end = start + sentence_end
                sentences.append(
                    {
                        "id": f"unit-{len(units) + 1:06d}-sentence-{sentence_order:03d}",
                        "label": f"{label}.{sentence_order}",
                        "sentence_order": sentence_order,
                        "text": markdown[absolute_start:absolute_end],
                        "source_span": {
                            "start": absolute_start,
                            "end": absolute_end,
                            "offset_unit": "unicode_code_point",
                        },
                    }
                )

        units.append(
            {
                "id": f"unit-{len(units) + 1:06d}",
                "label": label,
                "reading_order": len(units) + 1,
                "kind": kind,
                "text": text,
                "source_span": {
                    "start": start,
                    "end": end,
                    "offset_unit": "unicode_code_point",
                },
                "sentences": sentences,
            }
        )

    document = {
        "front_matter": front_matter,
        "normalized_markdown": markdown,
        "addressing": {
            "baseline": "L0",
            "top_level": "L<n> is the boundary after top-level reading unit n",
            "sentence": "L<n>.<m> is the boundary after sentence m within unit n",
            "public_aliases": ["L<n>-<m> resolves to L<n>.<m>"],
            "default_boundary": "after",
        },
        "units": units,
        "indexes": {
            "labels": _label_index(units),
            "reading_order": [unit["label"] for unit in units],
        },
    }
    validate_normalized_document(document)
    return document


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return trimmed sentence spans relative to one prose block.

    The heuristic avoids common abbreviations and decimal points. Structural
    blocks are never passed here, preventing punctuation in code, tables, or
    display mathematics from creating sentence boundaries.

    Example:
        ``sentence_spans("First. Second!") == [(0, 6), (7, 14)]``
    """

    spans: list[tuple[int, int]] = []
    sentence_start = 0
    index = 0
    while index < len(text):
        if text[index] not in ".!?":
            index += 1
            continue

        punctuation_end = index + 1
        while punctuation_end < len(text) and text[punctuation_end] in ".!?":
            punctuation_end += 1
        while punctuation_end < len(text) and text[punctuation_end] in '\"\'”’)]}':
            punctuation_end += 1

        if not _is_sentence_boundary(text, index, punctuation_end):
            index = punctuation_end
            continue

        start, end = _trim_span(text, sentence_start, punctuation_end)
        if end > start:
            spans.append((start, end))
        sentence_start = punctuation_end
        while sentence_start < len(text) and text[sentence_start].isspace():
            sentence_start += 1
        index = sentence_start

    start, end = _trim_span(text, sentence_start, len(text))
    if end > start:
        spans.append((start, end))
    return spans


def validate_normalized_document(document: dict[str, Any]) -> None:
    """Reject inconsistent ordering, labels, text slices, or sentence spans.

    Example:
        ``validate_normalized_document(normalize_markdown("Valid."))``
    """

    source = document["normalized_markdown"]
    seen_labels: set[str] = set()
    for expected_order, unit in enumerate(document["units"], start=1):
        if unit["reading_order"] != expected_order:
            raise ValueError("unit reading order is not consecutive")
        if unit["label"] != f"L{expected_order}":
            raise ValueError("unit label does not match numeric reading order")
        if unit["label"] in seen_labels:
            raise ValueError(f"duplicate label: {unit['label']}")
        seen_labels.add(unit["label"])
        _validate_text_span(source, unit)

        prior_end = unit["source_span"]["start"]
        for sentence_order, sentence in enumerate(unit["sentences"], start=1):
            expected_label = f"{unit['label']}.{sentence_order}"
            if sentence["label"] != expected_label:
                raise ValueError("sentence label does not match its unit and order")
            if sentence["label"] in seen_labels:
                raise ValueError(f"duplicate label: {sentence['label']}")
            seen_labels.add(sentence["label"])
            _validate_text_span(source, sentence)
            sentence_start = sentence["source_span"]["start"]
            sentence_end = sentence["source_span"]["end"]
            if sentence_start < prior_end or sentence_end > unit["source_span"]["end"]:
                raise ValueError("sentence span falls outside or overlaps its unit")
            prior_end = sentence_end


def canonicalize_position(position: str) -> str:
    """Return canonical ``L<n>`` or ``L<n>.<m>`` position syntax.

    The dotted form requested in early design notes is accepted as an alias.

    Example:
        ``canonicalize_position("l3-2") == "L3.2"``
    """

    match = re.fullmatch(r"[Ll](\d+)(?:[-.](\d+))?", position.strip())
    if match is None:
        raise ValueError(
            f"invalid position {position!r}; expected L<n>, L<n>.<m>, or L<n>-<m>"
        )
    unit_number = int(match.group(1))
    sentence_number = int(match.group(2)) if match.group(2) else None
    if unit_number < 1 or sentence_number == 0:
        raise ValueError("positions start at L1 and sentence indexes start at 1")
    return f"L{unit_number}" + (
        f".{sentence_number}" if sentence_number is not None else ""
    )


def _extract_front_matter(markdown: str) -> tuple[dict[str, Any] | None, int]:
    """Extract an initial YAML-like front matter slice without parsing YAML.

    Example:
        ``_extract_front_matter("---\\na: b\\n---\\nText")[1] > 0``
    """

    if not (markdown.startswith("---\n") or markdown == "---"):
        return None, 0
    match = re.search(r"\n(?:---|\.\.\.)[ \t]*(?:\n|$)", markdown[4:])
    if match is None:
        return None, 0
    closing_end = 4 + match.end()
    return {
        "raw": markdown[:closing_end].rstrip("\n"),
        "source_span": {
            "start": 0,
            "end": closing_end,
            "offset_unit": "unicode_code_point",
        },
        "reader_visible": False,
    }, closing_end


def _line_offsets(lines: list[str]) -> list[int]:
    """Return the source offset at the start of each line plus EOF.

    Example:
        ``_line_offsets(["a\\n", "b"]) == [0, 2, 3]``
    """

    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    return offsets


def _line_index_at_offset(offsets: list[int], source_offset: int) -> int:
    """Return the first line whose start is at or after an offset.

    Example:
        ``_line_index_at_offset([0, 2, 4], 2) == 1``
    """

    for index, offset in enumerate(offsets[:-1]):
        if offset >= source_offset:
            return index
    return max(0, len(offsets) - 1)


def _consume_block(lines: list[str], start: int) -> tuple[str, int]:
    """Classify and consume one Markdown block, returning an exclusive end.

    Example:
        ``_consume_block(["# Title\\n"], 0) == ("heading", 1)``
    """

    stripped = lines[start].rstrip("\n")
    fence = _FENCE_RE.match(stripped)
    if fence:
        marker = fence.group(1)
        end = start + 1
        closing = re.compile(rf"^[ \t]{{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*$")
        while end < len(lines):
            if closing.match(lines[end].rstrip("\n")):
                return "code_block", end + 1
            end += 1
        return "code_block", len(lines)

    if stripped.strip() in {"$$", "\\["}:
        closing_marker = "$$" if stripped.strip() == "$$" else "\\]"
        end = start + 1
        while end < len(lines):
            if lines[end].strip() == closing_marker:
                return "math_block", end + 1
            end += 1
        return "math_block", len(lines)

    if _HEADING_RE.match(stripped):
        return "heading", start + 1
    if _THEMATIC_RE.match(stripped):
        return "thematic_break", start + 1
    if _is_table_start(lines, start):
        end = start + 2
        while end < len(lines) and lines[end].strip() and "|" in lines[end]:
            end += 1
        return "table", end
    if _LIST_RE.match(stripped):
        end = start + 1
        while end < len(lines):
            candidate = lines[end].rstrip("\n")
            if not candidate.strip() or _LIST_RE.match(candidate):
                break
            if candidate.startswith((" ", "\t")):
                end += 1
                continue
            break
        return "list_item", end
    if stripped.lstrip().startswith(">"):
        end = start + 1
        while end < len(lines) and lines[end].lstrip().startswith(">"):
            end += 1
        return "blockquote", end
    if stripped.lstrip().startswith("<"):
        end = start + 1
        while end < len(lines) and lines[end].strip():
            end += 1
        return "html_block", end

    end = start + 1
    while end < len(lines) and lines[end].strip():
        candidate = lines[end].rstrip("\n")
        if _starts_structural_block(lines, end, candidate):
            break
        end += 1
    return "paragraph", end


def _starts_structural_block(lines: list[str], index: int, line: str) -> bool:
    """Return whether a line begins a structural block during prose scanning.

    Example:
        ``_starts_structural_block(["# H"], 0, "# H") is True``
    """

    return bool(
        _FENCE_RE.match(line)
        or _HEADING_RE.match(line)
        or _LIST_RE.match(line)
        or _THEMATIC_RE.match(line)
        or line.strip() in {"$$", "\\["}
        or line.lstrip().startswith((">", "<"))
        or _is_table_start(lines, index)
    )


def _is_table_start(lines: list[str], index: int) -> bool:
    """Return whether two lines form a Markdown table header and delimiter.

    Example:
        ``_is_table_start(["A | B\\n", "---|---\\n"], 0) is True``
    """

    return (
        index + 1 < len(lines)
        and "|" in lines[index]
        and bool(_TABLE_DELIMITER_RE.match(lines[index + 1].rstrip("\n")))
    )


def _trim_line_endings(source: str, start: int, end: int) -> int:
    """Remove trailing line endings from a block span while preserving spaces.

    Example:
        ``_trim_line_endings("a\\n", 0, 2) == 1``
    """

    while end > start and source[end - 1] in "\r\n":
        end -= 1
    return end


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim whitespace around a relative text span.

    Example:
        ``_trim_span(" x ", 0, 3) == (1, 2)``
    """

    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _is_sentence_boundary(text: str, punctuation: int, end: int) -> bool:
    """Return whether punctuation ends a sentence under the V0 heuristic.

    Example:
        ``_is_sentence_boundary("Value 1.5", 7, 8) is False``
    """

    if end < len(text) and not text[end].isspace():
        return False
    if text[punctuation] == ".":
        if punctuation > 0 and punctuation + 1 < len(text):
            if text[punctuation - 1].isdigit() and text[punctuation + 1].isdigit():
                return False
        prefix = text[: punctuation + 1]
        token_match = re.search(r"([A-Za-z](?:[A-Za-z.]*)\.)$", prefix)
        if token_match and token_match.group(1).lower() in _ABBREVIATIONS:
            return False
    return end == len(text) or text[end:].lstrip() != ""


def _label_index(units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build compact position metadata without duplicating source text.

    Example:
        ``_label_index([]) == {}``
    """

    index: dict[str, dict[str, Any]] = {}
    for unit in units:
        index[unit["label"]] = {
            "unit_id": unit["id"],
            "reading_order": unit["reading_order"],
            "kind": unit["kind"],
        }
        for sentence in unit["sentences"]:
            index[sentence["label"]] = {
                "unit_id": unit["id"],
                "sentence_id": sentence["id"],
                "reading_order": unit["reading_order"],
                "sentence_order": sentence["sentence_order"],
                "kind": "sentence",
            }
    return index


def _validate_text_span(source: str, record: dict[str, Any]) -> None:
    """Confirm a record's text is exactly the slice named by its source span.

    Example:
        ``_validate_text_span("x", {"text": "x", "source_span": {"start": 0, "end": 1}})``
    """

    start = record["source_span"]["start"]
    end = record["source_span"]["end"]
    if not (0 <= start <= end <= len(source)):
        raise ValueError("source span is outside normalized Markdown")
    if source[start:end] != record["text"]:
        raise ValueError("record text does not match its normalized source span")
