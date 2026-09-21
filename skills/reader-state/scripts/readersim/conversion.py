"""Convert supported source files to Markdown before normalization.

Markdown is read directly. Other formats use the project-selected Microsoft
MarkItDown command. No network-backed conversion or silent fallback is used.

Usage example::

    markdown, metadata = source_to_markdown(Path("paper.pdf"))
    print(metadata["converter"])
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


class ConversionError(RuntimeError):
    """Report an input or conversion failure with a user-actionable message."""


def source_to_markdown(source_path: Path) -> tuple[str, dict[str, Any]]:
    """Return normalized UTF-8 Markdown and conversion provenance.

    Args:
        source_path: Existing source file. ``.md`` and ``.markdown`` files are
            read directly; every other suffix is delegated to MarkItDown.

    Returns:
        A tuple containing Markdown text and conversion metadata.

    Raises:
        ConversionError: If the input is missing, unreadable, or cannot be
            converted by the installed MarkItDown command.

    Example:
        ``text, metadata = source_to_markdown(Path("notes.md"))``
    """

    if not source_path.is_file():
        raise ConversionError(f"input file does not exist: {source_path}")

    suffix = source_path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        try:
            text = source_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ConversionError(
                f"Markdown input is not valid UTF-8: {source_path}"
            ) from error
        except OSError as error:
            raise ConversionError(f"cannot read input file: {error}") from error

        return _normalize_newlines(text), {
            "converter": "native-markdown",
            "command": None,
            "source_media_type": "text/markdown",
            "warnings": [],
        }

    executable = shutil.which("markitdown")
    if executable is None:
        raise ConversionError(
            "MarkItDown is required for non-Markdown input but was not found on "
            "PATH. Install the PDF extra in an isolated environment, then retry: "
            "pip install 'markitdown[pdf]'"
        )

    try:
        completed = subprocess.run(
            [executable, str(source_path)],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="strict",
            text=True,
        )
    except (OSError, UnicodeError) as error:
        raise ConversionError(f"failed to execute MarkItDown: {error}") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or "no diagnostic was returned"
        raise ConversionError(
            f"MarkItDown exited with status {completed.returncode}: {detail}"
        )
    if not completed.stdout.strip():
        raise ConversionError("MarkItDown returned empty Markdown output")

    return _normalize_newlines(completed.stdout), {
        "converter": "microsoft-markitdown",
        "converter_version": _markitdown_version(executable),
        "command": ["markitdown", source_path.name],
        "source_media_type": _media_type_for_suffix(suffix),
        "warnings": [
            "Converted content may omit or flatten visual/layout information; "
            "inspect the normalized Markdown before reader simulation."
        ],
    }


def _normalize_newlines(text: str) -> str:
    """Convert CRLF and bare CR line endings to LF.

    Example:
        ``_normalize_newlines("a\\r\\nb") == "a\\nb"``
    """

    return text.replace("\r\n", "\n").replace("\r", "\n")


def _media_type_for_suffix(suffix: str) -> str:
    """Return a conservative media type for a known source suffix.

    Example:
        ``_media_type_for_suffix(".pdf") == "application/pdf"``
    """

    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".html": "text/html",
        ".htm": "text/html",
        ".txt": "text/plain",
    }.get(suffix, "application/octet-stream")


def _markitdown_version(executable: str) -> str | None:
    """Return MarkItDown's reported version without making conversion depend on it.

    Example:
        ``_markitdown_version("/missing/markitdown") is None``
    """

    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    version = completed.stdout.strip()
    return version or None
