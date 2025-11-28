"""Metric base classes and shared helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable, List, Set

from ..parsing import ParsedFile, ParsedFunction


@dataclass(frozen=True)
class MetricResult:
    """Named value produced by metrics."""

    name: str
    value: Any


class Metric(ABC):
    """Abstract metric interface."""

    name: str

    @abstractmethod
    def compute(self, parsed_file: ParsedFile) -> MetricResult:
        """Return a `MetricResult` for the provided parsed file."""


def is_code_line(line: str) -> bool:
    """Return True if line is code (ignores blanks/comments)."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    in_single = False
    in_double = False
    for idx, char in enumerate(stripped):
        if char == "'" and (idx == 0 or stripped[idx - 1] != "\\"):
            in_single = not in_single
        elif char == '"' and (idx == 0 or stripped[idx - 1] != "\\"):
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            stripped = stripped[:idx].strip()
            break
    return bool(stripped)


def calculate_cyclomatic_complexity(func_body: str) -> int:
    """Very rough cyclomatic complexity heuristic for R functions."""
    cc = 1
    patterns = [
        r"\bif\s*\(",
        r"\belse\b",
        r"\bwhile\s*\(",
        r"\bfor\s*\(",
        r"\brepeat\s*\(",
        r"\bbreak\b",
        r"\bnext\b",
        r"\bswitch\s*\(",
        r"\|\|",
        r"&&",
    ]
    import re

    for pattern in patterns:
        cc += len(re.findall(pattern, func_body))
    return cc


def count_function_calls(func_body: str) -> int:
    """Count method/function invocations within a function body."""
    import re

    pattern = r"\b\w+\s*\("
    excluded = {"if", "while", "for", "repeat", "switch", "function"}
    matches = re.findall(pattern, func_body)
    calls = [m.strip().rstrip("(") for m in matches]
    return sum(1 for call in calls if call not in excluded)


def extract_local_variables(func_body: str) -> Set[str]:
    """Collect variable names assigned or declared as parameters."""
    import re

    vars_set: Set[str] = set()
    assignment_patterns = [
        r"(\w+)\s*<-\s*",
        r"(\w+)\s*=\s*",
        r"(\w+)\s*<<-\s*",
    ]
    for pattern in assignment_patterns:
        vars_set.update(re.findall(pattern, func_body))
    param_match = re.search(r"function\s*\(([^)]*)\)", func_body)
    if param_match:
        params = [
            part.strip().split("=")[0].strip()
            for part in param_match.group(1).split(",")
            if part.strip()
        ]
        vars_set.update(params)
    return vars_set


def group_functions_by_class(functions: Iterable[ParsedFunction]) -> dict[str, List[str]]:
    """Group S3-like methods by class name."""
    grouped: dict[str, List[str]] = {}
    for func in functions:
        if func.class_name:
            grouped.setdefault(func.class_name, []).append(func.name)
    return grouped


def collect_classes(parsed_file: ParsedFile) -> dict[str, List[str]]:
    """Aggregate class structures (S3, R6, S4, RC) into a single mapping."""
    classes = group_functions_by_class(parsed_file.functions)
    for class_name, methods in parsed_file.r6_classes.items():
        classes.setdefault(class_name, []).extend(methods)
    for class_name, methods in parsed_file.s4_classes.items():
        classes.setdefault(class_name, []).extend(methods)
    for class_name, methods in parsed_file.rc_classes.items():
        classes.setdefault(class_name, []).extend(methods)
    return classes



