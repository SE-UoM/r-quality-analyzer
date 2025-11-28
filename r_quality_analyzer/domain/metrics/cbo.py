"""Coupling between objects metric."""

from __future__ import annotations

from .base import Metric, MetricResult
from ..parsing import ParsedFile


class CouplingBetweenObjectsMetric(Metric):
    name = "cbo"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        return MetricResult(self.name, len(set(parsed_file.imports)))


