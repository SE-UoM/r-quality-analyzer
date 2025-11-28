"""Methods per class metric."""

from __future__ import annotations

from .base import Metric, MetricResult, collect_classes, count_function_calls
from ..parsing import ParsedFile


class MethodsPerClassMetric(Metric):
    name = "mpc"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        classes = collect_classes(parsed_file)
        if classes:
            ratios = [len(methods) for methods in classes.values() if methods]
            ratio = (sum(ratios) / len(classes)) if classes else 0
        else:
            total_calls = sum(count_function_calls(func.body) for func in parsed_file.functions)
            ratio = (total_calls / len(parsed_file.functions)) if parsed_file.functions else total_calls
        return MetricResult(self.name, round(ratio, 2))


