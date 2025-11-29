"""
R Quality Analyzer - A tool for analyzing R code quality metrics.
"""

__version__ = "0.1.0"

from .analyzer import analyze_file, analyze_repo
from .cli import main

# Import lintr analyzer functions (optional)
try:
    from .lintr_analyzer import (
        check_lintr_available,
        run_lintr_on_file,
        run_lintr_on_directory,
        get_lintr_summary_for_file,
        get_lintr_summary_for_repo,
        parse_lintr_results
    )
    __all__ = [
        "analyze_file", 
        "analyze_repo", 
        "main",
        "check_lintr_available",
        "run_lintr_on_file",
        "run_lintr_on_directory",
        "get_lintr_summary_for_file",
        "get_lintr_summary_for_repo",
        "parse_lintr_results"
    ]
except ImportError:
    __all__ = ["analyze_file", "analyze_repo", "main"]


