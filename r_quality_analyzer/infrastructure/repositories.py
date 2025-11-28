"""Repository source abstractions for feeding R files into the analyzer."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Sequence, Tuple


R_EXTENSIONS: Tuple[str, ...] = (".r", ".R", ".Rmd")
SKIP_DIRECTORIES: Tuple[str, ...] = (".git", "node_modules", "__pycache__", ".Rproj.user")


class RepositorySource(ABC):
    """Provides access to R source files."""

    @abstractmethod
    def iter_files(self) -> Iterator[Tuple[str, str]]:
        """Yield `(path, contents)` for each R file available in the repository."""

    @abstractmethod
    def repo_name(self) -> str:
        """Return human-friendly name for reporting."""

    def cleanup(self) -> None:
        """Hook for subclasses that create temporary directories."""


@dataclass
class LocalRepositorySource(RepositorySource):
    """Repository source backed by a local directory on disk."""

    root_path: str
    repo_label: str | None = None
    origin: str | None = None
    extensions: Sequence[str] = R_EXTENSIONS
    skip_directories: Sequence[str] = SKIP_DIRECTORIES
    encoding: str = "utf-8"
    _paths_cache: List[str] = field(default_factory=list, init=False, repr=False, compare=False)

    def repo_name(self) -> str:
        if self.repo_label:
            return self.repo_label
        return os.path.basename(os.path.abspath(self.root_path))

    def iter_files(self) -> Iterator[Tuple[str, str]]:
        if not self._paths_cache:
            self._paths_cache.extend(self._collect_paths())
        for path in self._paths_cache:
            content = self._read_file(path)
            if content is not None:
                yield path, content

    def _collect_paths(self) -> List[str]:
        collected: List[str] = []
        for root, _, files in os.walk(self.root_path):
            if self._should_skip(root):
                continue
            for filename in files:
                if filename.endswith(tuple(self.extensions)):
                    collected.append(os.path.join(root, filename))
        return collected

    def _should_skip(self, root: str) -> bool:
        return any(segment in root for segment in self.skip_directories)

    def _read_file(self, path: str) -> str | None:
        try:
            with open(path, "r", encoding=self.encoding) as handle:
                return handle.read()
        except (OSError, UnicodeDecodeError):
            return None


