"""Deterministic document normalization for the Reader-State Simulator.

Usage example::

    from pathlib import Path
    from readersim.pipeline import compile_document

    output = compile_document(Path("draft.md"))
    print(output)
"""

from .pipeline import build_prefix, compile_document, load_artifact

__all__ = ["build_prefix", "compile_document", "load_artifact"]
__version__ = "0.1.0"
