"""Coordinates parsing and per-file metric computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .parsing import ParsedFile, RParser
from .metrics import (
    Metric,
    LinesOfCodeMetric,
    NumberOfFunctionsMetric,
    CyclomaticComplexityMetric,
    MethodsPerClassMetric,
    CouplingBetweenObjectsMetric,
    LackOfCohesionMetric,
    ParadigmDetectorMetric,
)


@dataclass(frozen=True)
class FileReport:
    """Immutable per-file analysis result."""

    path: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)


class FileAnalyzer:
    """Runs parser and metrics for a single file."""

    def __init__(
        self,
        parser: Optional[RParser] = None,
        metrics: Optional[Sequence[Metric]] = None,
        encoding: str = "utf-8",
    ) -> None:
        self.parser = parser or RParser()
        self.metrics: List[Metric] = list(
            metrics
            or [
                LinesOfCodeMetric(),
                NumberOfFunctionsMetric(),
                CyclomaticComplexityMetric(),
                MethodsPerClassMetric(),
                CouplingBetweenObjectsMetric(),
                LackOfCohesionMetric(),
                ParadigmDetectorMetric(),
            ]
        )
        self.encoding = encoding

    def analyze(self, path: str, source: Optional[str] = None) -> Optional[FileReport]:
        try:
            text = source if source is not None else self._read_file(path)
        except OSError:
            return None
        if text is None:
            return None
        parsed = self.parser.parse(path, text)
        metrics_data = self._run_metrics(parsed)
        metrics_data["file"] = path
        return FileReport(path=path, data=metrics_data)

    def _run_metrics(self, parsed: ParsedFile) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for metric in self.metrics:
            result = metric.compute(parsed)
            value = result.value
            if isinstance(value, dict):
                data.update(value)
            else:
                data[result.name] = value
        return data

    def _read_file(self, path: str) -> Optional[str]:
        try:
            with open(path, "r", encoding=self.encoding) as handle:
                return handle.read()
        except (OSError, UnicodeDecodeError):
            return None


