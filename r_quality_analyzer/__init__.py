"""
R Quality Analyzer - A tool for analyzing R code quality metrics.
"""

__version__ = "0.1.0"

from .analyzer import analyze_file, analyze_repo
from .cli import main

__all__ = ["analyze_file", "analyze_repo", "main"]


