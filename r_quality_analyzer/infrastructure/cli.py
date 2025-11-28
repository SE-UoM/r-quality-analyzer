"""Command-line interface orchestration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional, Sequence
from urllib.parse import urlparse

try:
    from git import Repo

    GIT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    GIT_AVAILABLE = False

from ..domain.file_analyzer import FileAnalyzer
from ..domain.repository_analyzer import RepositoryAnalyzer
from .repositories import LocalRepositorySource, RepositorySource


def is_git_url(path: str) -> bool:
    if os.path.exists(path):
        return False
    if path.startswith("git@"):
        return True
    parsed = urlparse(path)
    if parsed.scheme in {"http", "https", "ssh", "git"} and parsed.netloc:
        return True
    return path.endswith(".git") and "/" in path


def is_short_repo_format(path: str) -> bool:
    parts = path.split("/")
    return len(parts) == 2 and not path.startswith("http") and not os.path.exists(path)


def clone_remote_repo(repo: str, canonical_hint: Optional[str] = None) -> tuple[str, str]:
    if not GIT_AVAILABLE:
        raise ImportError("GitPython is required for cloning repositories. Run `pip install gitpython`.")
    temp_dir = tempfile.mkdtemp(prefix="r_quality_analyzer_")
    Repo.clone_from(repo, temp_dir)
    canonical_repo = canonical_hint or canonical_repo_identifier(repo)
    return temp_dir, canonical_repo


def canonical_repo_identifier(repo: str) -> str:
    sanitized = repo.strip()
    if sanitized.endswith(".git"):
        sanitized = sanitized[:-4]
    return sanitized.rstrip("/")


def repo_display_name(repo_identifier: str) -> str:
    trimmed = repo_identifier.rstrip("/")
    if ":" in trimmed and "/" not in trimmed.split(":")[-1]:
        tail = trimmed.split(":")[-1]
    else:
        tail = trimmed.split("/")[-1] if "/" in trimmed else trimmed
    if tail.endswith(".git"):
        tail = tail[:-4]
    return tail or trimmed


@dataclass
class CLIResult:
    exit_code: int
    payload: Optional[str] = None


class AnalyzerCLI:
    """Thin CLI wrapper that defers business logic to analyzers."""

    def __init__(self, file_analyzer: Optional[FileAnalyzer] = None) -> None:
        self.file_analyzer = file_analyzer or FileAnalyzer()

    def run(self, argv: Optional[Sequence[str]] = None) -> CLIResult:
        parser = self._build_parser()
        args = parser.parse_args(argv)
        if args.file:
            return self._analyze_single_file(args.target, args.output)
        return self._analyze_repository(args)

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Analyze R code quality metrics.")
        parser.add_argument("target", help="Git repo URL (supports short GitHub form) or local path")
        parser.add_argument("-o", "--output", help="Path to write JSON output", default=None)
        parser.add_argument("-f", "--file", help="Analyze a single file", action="store_true")
        parser.add_argument("--keep-clone", help="Keep cloned repo directory", action="store_true")
        return parser

    def _analyze_single_file(self, file_path: str, output_path: Optional[str]) -> CLIResult:
        if not os.path.isfile(file_path):
            return CLIResult(exit_code=1, payload=f"Error: File not found: {file_path}")
        report = self.file_analyzer.analyze(file_path)
        if report is None:
            return CLIResult(exit_code=1, payload=f"Error: Could not analyze file: {file_path}")
        payload = json.dumps({"file": report.to_dict(), "single_file": True}, indent=2)
        self._emit_output(payload, output_path)
        return CLIResult(exit_code=0, payload=payload)

    def _analyze_repository(self, args: argparse.Namespace) -> CLIResult:
        temp_dir: Optional[str] = None
        cleanup_needed = False
        try:
            source = self._resolve_source(args.target)
            if isinstance(source, tuple):
                temp_dir, repo_source = source
                cleanup_needed = temp_dir is not None and not args.keep_clone
            else:
                repo_source = source

            repo_analyzer = RepositoryAnalyzer(repo_source, self.file_analyzer)
            report = repo_analyzer.analyze().to_dict()
            payload = json.dumps(report, indent=2)
            self._emit_output(payload, args.output)
            return CLIResult(exit_code=0, payload=payload)
        except Exception as exc:  # pragma: no cover - CLI error surface
            return CLIResult(exit_code=1, payload=f"Error: {exc}")
        finally:
            if cleanup_needed and temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _resolve_source(self, target: str) -> RepositorySource | tuple[Optional[str], RepositorySource]:
        if is_short_repo_format(target):
            clone_url = f"https://github.com/{target}.git"
            canonical = f"https://github.com/{target}".rstrip("/")
            temp_dir, canonical_repo = clone_remote_repo(clone_url, canonical)
            return temp_dir, LocalRepositorySource(
                temp_dir,
                repo_label=repo_display_name(canonical_repo),
                origin=canonical_repo,
            )
        if is_git_url(target):
            temp_dir, canonical_repo = clone_remote_repo(target)
            return temp_dir, LocalRepositorySource(
                temp_dir,
                repo_label=repo_display_name(canonical_repo),
                origin=canonical_repo,
            )
        if not os.path.isdir(target):
            raise FileNotFoundError(f"Directory not found: {target}")
        abs_target = os.path.abspath(target)
        return LocalRepositorySource(
            abs_target,
            repo_label=os.path.basename(abs_target),
            origin=abs_target,
        )

    def _emit_output(self, payload: str, output_path: Optional[str]) -> None:
        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(payload)
        else:
            print(payload)


def main() -> None:
    cli = AnalyzerCLI()
    result = cli.run()
    if result.exit_code != 0 and result.payload:
        print(result.payload, file=sys.stderr)
    sys.exit(result.exit_code)


if __name__ == "__main__":  # pragma: no cover
    main()


