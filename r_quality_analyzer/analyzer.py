"""
R Code Quality Analyzer

Analyzes R code files and repositories for various quality metrics:
- LOC: Lines of Code
- NOM: Number of Methods/Functions
- CC_AVG: Average Cyclomatic Complexity
- MPC: Methods Per Class (functions per file for functional, methods per class for OOP)
- CBO: Coupling Between Objects (package dependencies)
- LCOM: Lack of Cohesion of Methods

Supports both functional and OOP R code (S3, S4, R6, Reference Classes).
"""

import os
import re
import json
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


# ---------------------------
# Utility Functions
# ---------------------------


def is_code_line(line: str) -> bool:
    """Return True if line is a code line (not blank or comment)."""
    line = line.strip()
    if not line:
        return False
    # Check if line starts with # (comment)
    if line.startswith("#"):
        return False
    # Remove inline comments (everything after # that's not in a string)
    # Simple approach: find # that's not inside quotes
    in_single_quote = False
    in_double_quote = False
    for i, char in enumerate(line):
        if char == "'" and (i == 0 or line[i-1] != '\\'):
            in_single_quote = not in_single_quote
        elif char == '"' and (i == 0 or line[i-1] != '\\'):
            in_double_quote = not in_double_quote
        elif char == '#' and not in_single_quote and not in_double_quote:
            line = line[:i].strip()
            break
    return bool(line)


def count_loc(filepath: str) -> int:
    """Count logical lines of code in an R file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return sum(1 for line in lines if is_code_line(line))
    except (UnicodeDecodeError, FileNotFoundError):
        return 0


def extract_functions(source: str) -> List[Tuple[str, str, int, Optional[str]]]:
    """
    Extract function definitions from R source code (both functional and OOP).
    Returns list of (function_name, function_body, start_line, class_name)
    class_name is None for functional code, or the class name for OOP methods.
    """
    functions = []
    lines = source.split('\n')
    
    # Pattern to match function definitions: name <- function(...) or name = function(...)
    # Also handles cases where assignment and function are on different lines
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for function definition pattern
        match = re.search(r'(\w+(?:\.\w+)?)\s*(?:<-|=)\s*function\s*\(', line)
        if match:
            func_name = match.group(1)
            start_line = i
            func_lines = [line]
            
            # Detect S3 methods (function names with dot notation like method.class)
            class_name = None
            if '.' in func_name and not func_name.startswith('.'):
                parts = func_name.split('.')
                if len(parts) == 2:
                    # Could be S3 method: method.class
                    class_name = parts[1]
            
            # Find where function(...) starts
            func_start_pos = line.find('function(')
            if func_start_pos == -1:
                # Multi-line function definition - look ahead
                j = i + 1
                while j < len(lines) and 'function(' not in lines[j]:
                    func_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    func_lines.append(lines[j])
                    func_start_pos = lines[j].find('function(')
                    i = j
                else:
                    i += 1
                    continue
            
            # Find the function body by matching braces (accounting for strings)
            brace_count = 0
            in_single_quote = False
            in_double_quote = False
            escape_next = False
            
            # Count braces in the current line from function position
            for char in line[func_start_pos:]:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif not in_single_quote and not in_double_quote:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
            
            j = i
            while j < len(lines) - 1 and brace_count > 0:
                j += 1
                func_lines.append(lines[j])
                line_content = lines[j]
                
                # Count braces in this line (accounting for strings)
                in_single_quote = False
                in_double_quote = False
                escape_next = False
                for char in line_content:
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == "'" and not in_double_quote:
                        in_single_quote = not in_single_quote
                    elif char == '"' and not in_single_quote:
                        in_double_quote = not in_double_quote
                    elif not in_single_quote and not in_double_quote:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
            
            func_body = '\n'.join(func_lines)
            functions.append((func_name, func_body, start_line, class_name))
            i = j + 1
        else:
            i += 1
    
    return functions


def extract_r6_classes(source: str) -> Dict[str, List[Tuple[str, str, int]]]:
    """
    Extract R6 classes and their methods.
    Returns dict mapping class_name -> list of (method_name, method_body, start_line)
    """
    classes = defaultdict(list)
    lines = source.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for R6Class definition: ClassName <- R6Class(...)
        r6_match = re.search(r'(\w+)\s*(?:<-|=)\s*R6Class\s*\(', line)
        if r6_match:
            class_name = r6_match.group(1)
            
            # Find the R6Class definition block
            brace_count = 0
            in_quote = False
            quote_char = None
            escape_next = False
            class_start = i
            class_lines = [line]
            
            # Find opening brace
            brace_pos = line.find('{')
            if brace_pos == -1:
                # Look ahead for opening brace
                j = i + 1
                while j < len(lines) and '{' not in lines[j]:
                    class_lines.append(lines[j])
                    j += 1
                if j < len(lines):
                    class_lines.append(lines[j])
                    brace_pos = lines[j].find('{')
                    i = j
                else:
                    i += 1
                    continue
            
            # Count braces to find class definition end
            for char in line[brace_pos:]:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char in ("'", '"') and not escape_next:
                    if not in_quote:
                        in_quote = True
                        quote_char = char
                    elif char == quote_char:
                        in_quote = False
                        quote_char = None
                elif not in_quote:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
            
            j = i
            while j < len(lines) - 1 and brace_count > 0:
                j += 1
                class_lines.append(lines[j])
                line_content = lines[j]
                
                in_quote = False
                quote_char = None
                escape_next = False
                for char in line_content:
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char in ("'", '"') and not escape_next:
                        if not in_quote:
                            in_quote = True
                            quote_char = char
                        elif char == quote_char:
                            in_quote = False
                            quote_char = None
                    elif not in_quote:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
            
            class_body = '\n'.join(class_lines)
            
            # Extract methods from class body (public, private, active)
            # Methods are defined as: method_name = function(...) or method_name <- function(...)
            method_pattern = r'(public|private|active)\s*=\s*list\s*\(([^)]+)\)'
            for match in re.finditer(method_pattern, class_body, re.DOTALL):
                methods_section = match.group(2)
                # Extract individual method definitions
                method_defs = re.finditer(r'(\w+)\s*(?:<-|=)\s*function\s*\(', methods_section)
                for method_match in method_defs:
                    method_name = method_match.group(1)
                    # Find method body (simplified - just mark as found)
                    classes[class_name].append((method_name, "", i))
            
            i = j + 1
        else:
            i += 1
    
    return dict(classes)


def extract_s4_classes(source: str) -> Dict[str, List[str]]:
    """
    Extract S4 classes and their methods.
    Returns dict mapping class_name -> list of method_names
    """
    classes = defaultdict(list)
    
    # Find setClass definitions
    setclass_pattern = r'setClass\s*\(\s*["\']?(\w+)["\']?'
    class_matches = re.findall(setclass_pattern, source)
    
    # Find setMethod definitions
    setmethod_pattern = r'setMethod\s*\(\s*["\']?(\w+)["\']?\s*,\s*["\']?(\w+)["\']?'
    method_matches = re.findall(setmethod_pattern, source)
    
    for method_name, class_name in method_matches:
        classes[class_name].append(method_name)
    
    # Also add classes that were defined but have no methods yet
    for class_name in class_matches:
        if class_name not in classes:
            classes[class_name] = []
    
    return dict(classes)


def extract_reference_classes(source: str) -> Dict[str, List[str]]:
    """
    Extract Reference Classes (RC) and their methods.
    Returns dict mapping class_name -> list of method_names
    """
    classes = defaultdict(list)
    
    # Find setRefClass definitions
    refclass_pattern = r'setRefClass\s*\(\s*["\']?(\w+)["\']?'
    class_matches = re.findall(refclass_pattern, source)
    
    # Methods in RC are defined within the class definition
    # Look for method definitions within class context
    for class_name in class_matches:
        # Find methods defined with $methods() or similar patterns
        # This is a simplified extraction
        method_pattern = rf'{class_name}\s*\.\s*(\w+)\s*(?:<-|=)\s*function'
        method_matches = re.findall(method_pattern, source)
        classes[class_name].extend(method_matches)
    
    return dict(classes)


def calculate_cyclomatic_complexity(func_body: str) -> int:
    """
    Calculate cyclomatic complexity for an R function.
    Complexity increases with: if, else, while, for, repeat, break, next, switch
    """
    cc = 1  # Base complexity
    
    # Count control flow statements
    patterns = [
        r'\bif\s*\(',
        r'\belse\b',
        r'\bwhile\s*\(',
        r'\bfor\s*\(',
        r'\brepeat\s*\(',
        r'\bbreak\b',
        r'\bnext\b',
        r'\bswitch\s*\(',
        r'\|\|',  # Logical OR
        r'&&',    # Logical AND
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, func_body)
        cc += len(matches)
    
    return cc


def count_function_calls(func_body: str) -> int:
    """Count method/function calls in a function body."""
    # Pattern to match function calls: name(...)
    # Exclude function definitions
    pattern = r'\b\w+\s*\('
    matches = re.findall(pattern, func_body)
    # Filter out control flow keywords
    excluded = {'if', 'while', 'for', 'repeat', 'switch', 'function'}
    calls = [m.strip().rstrip('(') for m in matches if m.strip().rstrip('(') not in excluded]
    return len(calls)


def extract_local_variables(func_body: str) -> Set[str]:
    """Extract local variable names from a function body."""
    vars_set = set()
    
    # Pattern for assignments: var <- value, var = value, var <<- value
    assignment_patterns = [
        r'(\w+)\s*<-\s*',
        r'(\w+)\s*=\s*',
        r'(\w+)\s*<<-\s*',
    ]
    
    for pattern in assignment_patterns:
        matches = re.findall(pattern, func_body)
        vars_set.update(matches)
    
    # Also get function parameters
    param_match = re.search(r'function\s*\(([^)]*)\)', func_body)
    if param_match:
        params = param_match.group(1)
        # Split by comma and extract parameter names
        param_names = [p.strip().split('=')[0].strip() for p in params.split(',') if p.strip()]
        vars_set.update(param_names)
    
    return vars_set


def analyze_functions(source: str) -> Tuple[List[int], List[Set[str]], int, int, Dict[str, List[str]], str]:
    """
    Analyze functions and OOP structures for complexity, local vars, and method calls.
    Returns: (complexities, func_vars, nom, total_method_calls, classes_dict, paradigm)
    paradigm is 'functional', 'oop', or 'mixed'
    """
    functions = extract_functions(source)
    complexities = []
    func_vars = []
    total_method_calls = 0
    
    # Detect OOP structures
    r6_classes = extract_r6_classes(source)
    s4_classes = extract_s4_classes(source)
    rc_classes = extract_reference_classes(source)
    
    # Group functions by class (for S3 methods)
    classes_dict = defaultdict(list)
    functional_functions = []
    
    for func_name, func_body, _, class_name in functions:
        cc = calculate_cyclomatic_complexity(func_body)
        complexities.append(cc)
        
        local_vars = extract_local_variables(func_body)
        func_vars.append(local_vars)
        
        method_calls = count_function_calls(func_body)
        total_method_calls += method_calls
        
        # Group S3 methods by class
        if class_name:
            classes_dict[class_name].append(func_name)
        else:
            functional_functions.append(func_name)
    
    # Add R6, S4, and RC classes
    for class_name, methods in r6_classes.items():
        classes_dict[class_name].extend([m[0] for m in methods])
    
    for class_name, methods in s4_classes.items():
        classes_dict[class_name].extend(methods)
    
    for class_name, methods in rc_classes.items():
        classes_dict[class_name].extend(methods)
    
    # Determine paradigm
    has_oop = len(classes_dict) > 0 or len(r6_classes) > 0 or len(s4_classes) > 0 or len(rc_classes) > 0
    has_functional = len(functional_functions) > 0
    
    if has_oop and has_functional:
        paradigm = 'mixed'
    elif has_oop:
        paradigm = 'oop'
    else:
        paradigm = 'functional'
    
    nom = len(functions)
    return complexities, func_vars, nom, total_method_calls, dict(classes_dict), paradigm


def calculate_lcom(func_vars: List[Set[str]], classes_dict: Dict[str, List[str]] = None) -> int:
    """
    Calculate Lack of Cohesion of Methods (LCOM).
    For OOP: calculates LCOM per class and averages.
    For functional: calculates LCOM across all functions in file.
    """
    if len(func_vars) < 2:
        return 0
    
    # If we have classes, calculate LCOM per class
    if classes_dict and len(classes_dict) > 0:
        class_lcoms = []
        # For each class, calculate LCOM of its methods
        # This is simplified - we'd need to map methods to their func_vars
        # For now, calculate overall LCOM
        lcom = 0
        n = len(func_vars)
        for i in range(n):
            for j in range(i + 1, n):
                if func_vars[i].isdisjoint(func_vars[j]):
                    lcom += 1
        return lcom
    else:
        # Functional code: calculate LCOM across all functions
        lcom = 0
        n = len(func_vars)
        for i in range(n):
            for j in range(i + 1, n):
                if func_vars[i].isdisjoint(func_vars[j]):
                    lcom += 1
        return lcom


def analyze_imports(source: str) -> int:
    """
    Count number of unique imported packages (proxy for coupling).
    Looks for library(), require(), source(), and :: usage.
    """
    packages = set()
    
    # library() and require() calls
    library_pattern = r'(?:library|require)\s*\(\s*["\']?([^"\']+)["\']?\s*\)'
    matches = re.findall(library_pattern, source, re.IGNORECASE)
    packages.update(matches)
    
    # source() calls (file imports)
    source_pattern = r'source\s*\(\s*["\']([^"\']+)["\']'
    source_matches = re.findall(source_pattern, source, re.IGNORECASE)
    packages.update([f"source:{s}" for s in source_matches])
    
    # Package::function usage
    namespace_pattern = r'(\w+)::\w+'
    namespace_matches = re.findall(namespace_pattern, source)
    packages.update(namespace_matches)
    
    return len(packages)


# ---------------------------
# Main Analyzer
# ---------------------------


def analyze_file(filepath: str) -> Optional[Dict]:
    """Analyze a single R file and return its metrics (supports both functional and OOP)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception:
        # Skip unreadable or invalid R files
        return None
    
    loc = count_loc(filepath)
    functions = extract_functions(source)
    complexities = []
    func_vars = []
    total_method_calls = 0
    
    # Detect OOP structures
    r6_classes = extract_r6_classes(source)
    s4_classes = extract_s4_classes(source)
    rc_classes = extract_reference_classes(source)
    
    # Group functions by class (for S3 methods)
    classes_dict = defaultdict(list)
    functional_functions = []
    
    # Build complexities array with function-level details
    function_complexities = []
    
    for func_name, func_body, start_line, class_name in functions:
        cc = calculate_cyclomatic_complexity(func_body)
        complexities.append(cc)
        function_complexities.append({
            "function": func_name,
            "start_line": start_line + 1,  # Convert to 1-based line numbers
            "cc": cc
        })
        
        local_vars = extract_local_variables(func_body)
        func_vars.append(local_vars)
        
        method_calls = count_function_calls(func_body)
        total_method_calls += method_calls
        
        # Group S3 methods by class
        if class_name:
            classes_dict[class_name].append(func_name)
        else:
            functional_functions.append(func_name)
    
    # Add R6, S4, and RC classes
    for class_name, methods in r6_classes.items():
        classes_dict[class_name].extend([m[0] for m in methods])
    
    for class_name, methods in s4_classes.items():
        classes_dict[class_name].extend(methods)
    
    for class_name, methods in rc_classes.items():
        classes_dict[class_name].extend(methods)
    
    # Determine paradigm
    has_oop = len(classes_dict) > 0 or len(r6_classes) > 0 or len(s4_classes) > 0 or len(rc_classes) > 0
    has_functional = len(functional_functions) > 0
    
    if has_oop and has_functional:
        paradigm = 'mixed'
    elif has_oop:
        paradigm = 'oop'
    else:
        paradigm = 'functional'
    
    nom = len(functions)
    avg_cc = sum(complexities) / len(complexities) if complexities else 0
    lcom = calculate_lcom(func_vars, classes_dict)
    cbo = analyze_imports(source)
    
    # MPC: Methods Per Class
    # For OOP: average methods per class
    # For functional: functions per file (or ratio of method calls to functions)
    if paradigm in ('oop', 'mixed') and len(classes_dict) > 0:
        # Calculate average methods per class
        methods_per_class = [len(methods) for methods in classes_dict.values()]
        mpc_ratio = sum(methods_per_class) / len(classes_dict) if classes_dict else 0
    else:
        # Functional: use ratio of method calls to functions
        mpc_ratio = (total_method_calls / nom) if nom > 0 else total_method_calls
    
    result = {
        "loc": loc,
        "nom": nom,
        "cc_avg": round(avg_cc, 2),
        "complexities": function_complexities,
        "mpc": round(mpc_ratio, 2),
        "cbo": cbo,
        "lcom": lcom,
        "paradigm": paradigm,
        "classes": {name: len(methods) for name, methods in classes_dict.items()} if classes_dict else {},
        "num_classes": len(classes_dict),
        "file": filepath,
    }
    
    return result


def analyze_repo(repo_path: str, repo_url: Optional[str] = None) -> Dict:
    """
    Analyze all R files in a repository folder.
    
    Args:
        repo_path: Path to the repository folder
        repo_url: Optional repository URL (e.g., GitHub URL)
    
    Returns aggregated metrics in a JSON-like dict.
    """
    results = []
    r_extensions = [".r", ".R", ".Rmd"]
    
    for root, _, files in os.walk(repo_path):
        # Skip common directories
        if any(skip in root for skip in [".git", "node_modules", "__pycache__", ".Rproj.user"]):
            continue
            
        for file in files:
            if any(file.endswith(ext) for ext in r_extensions):
                filepath = os.path.join(root, file)
                metrics = analyze_file(filepath)
                if metrics:
                    results.append(metrics)
    
    # Determine repo name and URL
    if repo_url:
        # Extract repo name from URL
        if 'github.com' in repo_url:
            # Extract from https://github.com/user/repo or https://github.com/user/repo.git
            parts = repo_url.rstrip('/').rstrip('.git').split('/')
            repo_name = parts[-1] if parts else os.path.basename(repo_path)
            # Normalize URL (remove .git if present, ensure it's https://)
            if repo_url.endswith('.git'):
                normalized_url = repo_url[:-4]
            else:
                normalized_url = repo_url
            if not normalized_url.startswith('http'):
                normalized_url = f"https://github.com/{normalized_url}"
        else:
            repo_name = os.path.basename(repo_path)
            normalized_url = repo_url
    else:
        repo_name = os.path.basename(repo_path)
        normalized_url = None
    
    # Aggregate repository-level metrics
    if not results:
        return {
            "repo": normalized_url or "",
            "repo_name": repo_name,
            "local_repo": os.path.abspath(repo_path),
            "total_files": 0,
            "total_loc": 0,
            "total_nom": 0,
            "avg_cc": 0,
            "avg_mpc": 0,
            "total_cbo": 0,
            "avg_lcom": 0,
            "paradigm": "functional",
            "paradigm_distribution": {},
            "total_classes": 0,
            "files": [],
        }
    
    total_loc = sum(r["loc"] for r in results)
    total_nom = sum(r["nom"] for r in results)
    total_cbo = sum(r["cbo"] for r in results)
    avg_cc = round(sum(r["cc_avg"] for r in results) / len(results), 2) if results else 0
    avg_mpc = round(sum(r["mpc"] for r in results) / len(results), 2) if results else 0
    avg_lcom = round(sum(r["lcom"] for r in results) / len(results), 2) if results else 0
    
    # Count paradigms
    paradigms = [r.get("paradigm", "functional") for r in results]
    paradigm_counts = {}
    for p in paradigms:
        paradigm_counts[p] = paradigm_counts.get(p, 0) + 1
    
    # Determine overall paradigm
    if len(paradigm_counts) == 1:
        overall_paradigm = list(paradigm_counts.keys())[0]
    elif "mixed" in paradigm_counts:
        overall_paradigm = "mixed"
    elif "oop" in paradigm_counts and "functional" in paradigm_counts:
        overall_paradigm = "mixed"
    else:
        overall_paradigm = max(paradigm_counts, key=paradigm_counts.get) if paradigm_counts else "functional"
    
    # Count total classes across all files
    total_classes = sum(r.get("num_classes", 0) for r in results)
    
    summary = {
        "repo": normalized_url or "",
        "repo_name": repo_name,
        "local_repo": os.path.abspath(repo_path),
        "total_files": len(results),
        "total_loc": total_loc,
        "total_nom": total_nom,
        "avg_cc": avg_cc,
        "avg_mpc": avg_mpc,
        "total_cbo": total_cbo,
        "avg_lcom": avg_lcom,
        "paradigm": overall_paradigm,
        "paradigm_distribution": paradigm_counts,
        "total_classes": total_classes,
        "files": results,
    }
    
    return summary

