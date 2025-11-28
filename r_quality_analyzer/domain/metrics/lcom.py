"""Lack of cohesion metric."""

from __future__ import annotations

from .base import Metric, MetricResult, collect_classes, extract_local_variables
from ..parsing import ParsedFile


class LackOfCohesionMetric(Metric):
    name = "lcom"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        func_vars = [extract_local_variables(func.body) for func in parsed_file.functions]
        if len(func_vars) < 2:
            return MetricResult(self.name, 0)
        lcom = 0
        for i in range(len(func_vars)):
            for j in range(i + 1, len(func_vars)):
                if func_vars[i].isdisjoint(func_vars[j]):
                    lcom += 1
        return MetricResult(self.name, lcom)


