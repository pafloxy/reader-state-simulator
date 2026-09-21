"""Command-line interface for the deterministic ReaderSim normalization slice.

Usage examples, run from the repository root::

    ./readersim compile tests/fixtures/example.md
    ./readersim query-at example.reader-state-simulation.json L3.1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .pipeline import (
    ArtifactError,
    build_prefix,
    compile_document,
    load_artifact,
    write_json_result,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser and its compile/query-at command contracts.

    Example:
        ``parser = build_parser(); parser.parse_args(["compile", "draft.md"])``
    """

    parser = argparse.ArgumentParser(
        prog="readersim",
        description=(
            "Normalize a source document to addressable JSON and emit strict "
            "reader-visible prefixes. Reader-state inference is not implemented yet."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    compile_parser = subparsers.add_parser(
        "compile",
        help="convert if needed and normalize a source document to JSON",
    )
    compile_parser.add_argument("source", type=Path, help="Markdown or supported source file")
    compile_parser.add_argument(
        "-o", "--output", type=Path, help="output JSON path (default: beside source)"
    )
    compile_parser.add_argument(
        "--indent", type=int, default=2, choices=range(0, 9), metavar="0..8"
    )

    query_parser = subparsers.add_parser(
        "query-at",
        help="emit a suffix-free prefix bundle at an address",
    )
    query_parser.add_argument("artifact", type=Path, help="compiled normalized JSON")
    query_parser.add_argument(
        "position", help="L<n>, L<n>.<m>, or hyphenated alias L<n>-<m>"
    )
    query_parser.add_argument("-o", "--output", type=Path, help="write JSON instead of stdout")
    query_parser.add_argument(
        "--indent", type=int, default=2, choices=range(0, 9), metavar="0..8"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one CLI operation and return a process status code.

    Status ``0`` means success, ``2`` means a documented input/conversion/
    artifact failure, and argparse also uses ``2`` for invalid command syntax.

    Example:
        ``status = main(["compile", "draft.md", "-o", "draft.json"])``
    """

    args = build_parser().parse_args(argv)
    try:
        if args.command == "compile":
            destination = compile_document(args.source, args.output, indent=args.indent)
            print(destination)
            return 0

        artifact = load_artifact(args.artifact)
        result = build_prefix(artifact, args.position)
        stdout_text = write_json_result(result, args.output, indent=args.indent)
        if stdout_text is not None:
            sys.stdout.write(stdout_text)
        elif args.output is not None:
            print(args.output.expanduser().resolve())
        return 0
    except (ArtifactError, ValueError) as error:
        print(f"readersim: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
