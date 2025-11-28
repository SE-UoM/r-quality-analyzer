"""Compatibility API for the refactored R quality analyzer."""

from __future__ import annotations

import os
from typing import Dict, Optional

from .domain.file_analyzer import FileAnalyzer
from .domain.repository_analyzer import RepositoryAnalyzer
from .infrastructure.repositories import LocalRepositorySource


_FILE_ANALYZER = FileAnalyzer()


def analyze_file(filepath: str) -> Optional[Dict]:
    """Analyze a single R file via the modular analyzer."""
    report = _FILE_ANALYZER.analyze(filepath)
    return report.to_dict() if report else None


def analyze_repo(repo_path: str) -> Dict:
    """Analyze a repository via the modular analyzer."""
    abs_repo_path = os.path.abspath(repo_path)
    source = LocalRepositorySource(
        abs_repo_path,
        repo_label=os.path.basename(abs_repo_path),
        origin=abs_repo_path,
    )
    analyzer = RepositoryAnalyzer(source, _FILE_ANALYZER)
    return analyzer.analyze().to_dict()


