"""Lines of code metric."""

from __future__ import annotations

from .base import Metric, MetricResult, is_code_line
from ..parsing import ParsedFile


class LinesOfCodeMetric(Metric):
    name = "loc"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        loc = sum(1 for line in parsed_file.source.splitlines() if is_code_line(line))
        return MetricResult(self.name, loc)


