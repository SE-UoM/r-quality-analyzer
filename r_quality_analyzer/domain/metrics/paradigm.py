"""Paradigm detection metric."""

from __future__ import annotations

from .base import Metric, MetricResult, collect_classes
from ..parsing import ParsedFile


class ParadigmDetectorMetric(Metric):
    name = "paradigm"

    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        classes = collect_classes(parsed_file)
        has_oop = bool(classes)
        has_functional = any(func.class_name is None for func in parsed_file.functions)
        if has_oop and has_functional:
            paradigm = "mixed"
        elif has_oop:
            paradigm = "oop"
        else:
            paradigm = "functional"
        value = {
            "paradigm": paradigm,
            "classes": {name: len(methods) for name, methods in classes.items()},
            "num_classes": len(classes),
        }
        return MetricResult(self.name, value)


