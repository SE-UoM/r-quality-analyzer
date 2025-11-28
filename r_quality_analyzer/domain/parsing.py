"""R code parsing utilities used by the analyzer domain layer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class ParsedFunction:
    """Captured function metadata from an R source file."""

    name: str
    body: str
    start_line: int
    class_name: Optional[str]


@dataclass(frozen=True)
class ParsedFile:
    """Structured representation of an R source file."""

    path: str
    source: str
    functions: List[ParsedFunction]
    r6_classes: Dict[str, List[str]]
    s4_classes: Dict[str, List[str]]
    rc_classes: Dict[str, List[str]]
    imports: List[str]


class RParser:
    """Parses raw R source text into structured components."""

    def parse(self, path: str, source: str) -> ParsedFile:
        functions = self._extract_functions(source)
        r6_classes = self._extract_r6_classes(source)
        s4_classes = self._extract_s4_classes(source)
        rc_classes = self._extract_reference_classes(source)
        imports = self._extract_imports(source)

        return ParsedFile(
            path=path,
            source=source,
            functions=functions,
            r6_classes=r6_classes,
            s4_classes=s4_classes,
            rc_classes=rc_classes,
            imports=imports,
        )

    def _extract_functions(self, source: str) -> List[ParsedFunction]:
        functions: List[ParsedFunction] = []
        lines = source.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            match = re.search(r"(\w+(?:\.\w+)?)\s*(?:<-|=)\s*function\s*\(", line)
            if not match:
                i += 1
                continue

            func_name = match.group(1)
            start_line = i
            func_lines = [line]
            class_name = self._detect_s3_class(func_name)

            func_start_pos = line.find("function(")
            if func_start_pos == -1:
                j = i + 1
                while j < len(lines) and "function(" not in lines[j]:
                    func_lines.append(lines[j])
                    j += 1
                if j >= len(lines):
                    i += 1
                    continue
                func_lines.append(lines[j])
                func_start_pos = lines[j].find("function(")
                i = j
            brace_count = self._count_braces(line[func_start_pos:])

            j = i
            while j < len(lines) - 1 and brace_count > 0:
                j += 1
                func_lines.append(lines[j])
                brace_count += self._count_braces(lines[j])

            func_body = "\n".join(func_lines)
            functions.append(ParsedFunction(func_name, func_body, start_line, class_name))
            i = j + 1
        return functions

    def _detect_s3_class(self, func_name: str) -> Optional[str]:
        if "." not in func_name or func_name.startswith("."):
            return None
        parts = func_name.split(".")
        if len(parts) == 2:
            return parts[1]
        return None

    def _count_braces(self, text: str) -> int:
        brace_count = 0
        in_single_quote = False
        in_double_quote = False
        escape_next = False
        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif char == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
        return brace_count

    def _extract_r6_classes(self, source: str) -> Dict[str, List[str]]:
        classes: Dict[str, List[str]] = {}
        lines = source.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            r6_match = re.search(r"(\w+)\s*(?:<-|=)\s*R6Class\s*\(", line)
            if not r6_match:
                i += 1
                continue

            class_name = r6_match.group(1)
            class_block, next_index = self._extract_block(lines, i)
            i = next_index
            classes[class_name] = self._extract_r6_methods(class_block)
        return classes

    def _extract_block(self, lines: List[str], start_idx: int) -> Tuple[str, int]:
        brace_count = 0
        in_quote = False
        quote_char = ""
        escape_next = False
        block_lines = []
        j = start_idx
        started = False
        while j < len(lines):
            line = lines[j]
            block_lines.append(line)
            for char in line:
                if escape_next:
                    escape_next = False
                    continue
                if char == "\\":
                    escape_next = True
                    continue
                if char in ("'", '"'):
                    if not in_quote:
                        in_quote = True
                        quote_char = char
                    elif char == quote_char:
                        in_quote = False
                        quote_char = ""
                elif not in_quote:
                    if char == "{":
                        brace_count += 1
                        started = True
                    elif char == "}" and started:
                        brace_count -= 1
            if started and brace_count == 0:
                break
            j += 1
        return "\n".join(block_lines), j + 1

    def _extract_r6_methods(self, class_body: str) -> List[str]:
        methods: List[str] = []
        method_pattern = r"(public|private|active)\s*=\s*list\s*\(([^)]+)\)"
        for match in re.finditer(method_pattern, class_body, re.DOTALL):
            methods_section = match.group(2)
            method_defs = re.finditer(r"(\w+)\s*(?:<-|=)\s*function\s*\(", methods_section)
            for method_match in method_defs:
                methods.append(method_match.group(1))
        return methods

    def _extract_s4_classes(self, source: str) -> Dict[str, List[str]]:
        classes: Dict[str, List[str]] = {}
        class_pattern = r"setClass\s*\(\s*[\"']?(\w+)[\"']?"
        method_pattern = r"setMethod\s*\(\s*[\"']?(\w+)[\"']?\s*,\s*[\"']?(\w+)[\"']?"
        for class_name in re.findall(class_pattern, source):
            classes[class_name] = []
        for method_name, class_name in re.findall(method_pattern, source):
            classes.setdefault(class_name, []).append(method_name)
        return classes

    def _extract_reference_classes(self, source: str) -> Dict[str, List[str]]:
        classes: Dict[str, List[str]] = {}
        refclass_pattern = r"setRefClass\s*\(\s*[\"']?(\w+)[\"']?"
        for class_name in re.findall(refclass_pattern, source):
            method_pattern = rf"{class_name}\s*\.\s*(\w+)\s*(?:<-|=)\s*function"
            methods = re.findall(method_pattern, source)
            classes[class_name] = methods
        return classes

    def _extract_imports(self, source: str) -> List[str]:
        packages = set()
        library_pattern = r"(?:library|require)\s*\(\s*[\"']?([^\"']+)[\"']?\s*\)"
        packages.update(re.findall(library_pattern, source, re.IGNORECASE))
        source_pattern = r"source\s*\(\s*[\"']([^\"']+)[\"']"
        packages.update(f"source:{match}" for match in re.findall(source_pattern, source))
        namespace_pattern = r"(\w+)::\w+"
        packages.update(re.findall(namespace_pattern, source))
        return sorted(packages)


