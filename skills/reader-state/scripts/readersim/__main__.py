"""Run ReaderSim through ``python -m readersim``.

Usage example::

    PYTHONPATH=src python3 -m readersim --help
"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
