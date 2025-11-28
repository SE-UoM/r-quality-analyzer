"""Backward-compatible CLI entrypoint."""

from __future__ import annotations

from .infrastructure.cli import AnalyzerCLI, main

__all__ = ["AnalyzerCLI", "main"]


if __name__ == "__main__":  # pragma: no cover
    main()


