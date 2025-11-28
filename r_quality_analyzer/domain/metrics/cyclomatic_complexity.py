"""Cyclomatic complexity metric."""

from __future__ import annotations

from statistics import mean
from typing import Dict, List

from .base import Metric, MetricResult, calculate_cyclomatic_complexity
from ..parsing import ParsedFile


class CyclomaticComplexityMetric(Metric):
    name = "cc"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        per_function: List[Dict[str, int]] = []
        scores: List[int] = []
        for function in parsed_file.functions:
            complexity = calculate_cyclomatic_complexity(function.body)
            scores.append(complexity)
            per_function.append(
                {
                    "function": function.name,
                    "start_line": function.start_line + 1,
                    "cc": complexity,
                }
            )
        avg = round(mean(scores), 2) if scores else 0
        return MetricResult(self.name, {"cc_avg": avg, "complexities": per_function})


