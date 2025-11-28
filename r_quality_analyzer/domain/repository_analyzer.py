"""Aggregates metrics across repository sources."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..infrastructure.repositories import RepositorySource
from .file_analyzer import FileAnalyzer, FileReport


@dataclass(frozen=True)
class RepositoryReport:
    """Aggregate analysis result for a repository."""

    repo: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)


class RepositoryAnalyzer:
    """Coordinates repository traversal and per-file analysis."""

    def __init__(self, source: RepositorySource, file_analyzer: Optional[FileAnalyzer] = None) -> None:
        self.source = source
        self.file_analyzer = file_analyzer or FileAnalyzer()

    def analyze(self) -> RepositoryReport:
        file_results: List[Dict[str, Any]] = []
        try:
            for path, text in self.source.iter_files():
                report = self.file_analyzer.analyze(path, text)
                if report:
                    file_results.append(report.to_dict())
        finally:
            self.source.cleanup()
        summary = self._build_summary(file_results)
        repo_identifier = getattr(self.source, "origin", None) or self.source.repo_name()
        return RepositoryReport(repo=repo_identifier, data=summary)

    def _build_summary(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        repo_name = self.source.repo_name()
        repo_identifier = getattr(self.source, "origin", None) or repo_name
        root_path = getattr(self.source, "root_path", None)
        local_repo = os.path.abspath(root_path) if root_path else None
        if not files:
            return {
                "repo": repo_identifier,
                "repo_name": repo_name,
                "local_repo": local_repo,
                "total_files": 0,
                "total_loc": 0,
                "total_nom": 0,
                "avg_cc": 0,
                "avg_mpc": 0,
                "total_cbo": 0,
                "avg_lcom": 0,
                "paradigm": "functional",
                "paradigm_distribution": {},
                "total_classes": 0,
                "files": [],
            }

        total_files = len(files)
        total_loc = sum(f.get("loc", 0) for f in files)
        total_nom = sum(f.get("nom", 0) for f in files)
        total_cbo = sum(f.get("cbo", 0) for f in files)
        avg_cc = round(sum(f.get("cc_avg", 0) for f in files) / total_files, 2)
        avg_mpc = round(sum(f.get("mpc", 0) for f in files) / total_files, 2)
        avg_lcom = round(sum(f.get("lcom", 0) for f in files) / total_files, 2)

        paradigm_counts: Dict[str, int] = {}
        for file_data in files:
            paradigm = file_data.get("paradigm", "functional")
            paradigm_counts[paradigm] = paradigm_counts.get(paradigm, 0) + 1

        overall_paradigm = self._derive_overall_paradigm(paradigm_counts)
        total_classes = sum(file_data.get("num_classes", 0) for file_data in files)

        return {
            "repo": repo_identifier,
            "repo_name": repo_name,
            "local_repo": local_repo,
            "total_files": total_files,
            "total_loc": total_loc,
            "total_nom": total_nom,
            "avg_cc": avg_cc,
            "avg_mpc": avg_mpc,
            "total_cbo": total_cbo,
            "avg_lcom": avg_lcom,
            "paradigm": overall_paradigm,
            "paradigm_distribution": paradigm_counts,
            "total_classes": total_classes,
            "files": files,
        }

    def _derive_overall_paradigm(self, counts: Dict[str, int]) -> str:
        if not counts:
            return "functional"
        if len(counts) == 1:
            return next(iter(counts))
        if "mixed" in counts or ("oop" in counts and "functional" in counts):
            return "mixed"
        return max(counts, key=counts.get)


