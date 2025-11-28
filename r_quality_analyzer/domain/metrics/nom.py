"""Number of functions metric."""

from __future__ import annotations

from .base import Metric, MetricResult
from ..parsing import ParsedFile


class NumberOfFunctionsMetric(Metric):
    name = "nom"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        return MetricResult(self.name, len(parsed_file.functions))


