"""
Lintr Analyzer - A dedicated module for running and parsing lintr analysis on R code.

This module provides functions to:
- Run lintr on R files or directories
- Parse lintr output
- Integrate lintr results with the main analyzer
"""

import os
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path


def check_r_available() -> Tuple[bool, Optional[str]]:
    """
    Check if R is installed and available.
    
    Returns:
        Tuple of (is_available, error_message)
    """
    try:
        result = subprocess.run(
            ["Rscript", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, None
        else:
            return False, "R is installed but Rscript command failed"
    except FileNotFoundError:
        return False, "R is not installed. Please install R from https://cran.r-project.org/"
    except subprocess.TimeoutExpired:
        return False, "R check timed out"
    except Exception as e:
        return False, f"Error checking R: {str(e)}"


def check_lintr_available(install_if_missing: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Check if lintr R package is available in the system.
    Optionally installs it if missing.
    
    Args:
        install_if_missing: If True, attempts to install lintr if not available
    
    Returns:
        Tuple of (is_available, error_message)
    """
    # First check if R is available
    r_available, r_error = check_r_available()
    if not r_available:
        return False, r_error
    
    try:
        # Try to run R and check if lintr is installed
        r_script = """
        if (!requireNamespace("lintr", quietly = TRUE)) {
            quit(status = 1, save = "no")
        }
        quit(status = 0, save = "no")
        """
        
        result = subprocess.run(
            ["Rscript", "--vanilla", "-e", r_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # If lintr is not available and we should install it
        if result.returncode != 0 and install_if_missing:
            # Try to install lintr
            install_script = """
            if (!requireNamespace("lintr", quietly = TRUE)) {
                tryCatch({
                    install.packages("lintr", repos = "https://cloud.r-project.org", quiet = TRUE)
                    if (requireNamespace("lintr", quietly = TRUE)) {
                        quit(status = 0, save = "no")
                    } else {
                        quit(status = 1, save = "no")
                    }
                }, error = function(e) {
                    cat("Installation error:", conditionMessage(e), "\\n", file = stderr())
                    quit(status = 1, save = "no")
                })
            } else {
                quit(status = 0, save = "no")
            }
            """
            
            install_result = subprocess.run(
                ["Rscript", "--vanilla", "-e", install_script],
                capture_output=True,
                text=True,
                timeout=120  # Installation can take time
            )
            
            if install_result.returncode == 0:
                return True, None
            else:
                error_msg = install_result.stderr.strip() or install_result.stdout.strip()
                return False, f"Failed to install lintr: {error_msg if error_msg else 'Unknown error'}"
        
        if result.returncode == 0:
            return True, None
        else:
            return False, "lintr package is not installed"
            
    except (subprocess.TimeoutExpired, Exception) as e:
        return False, f"Error checking lintr: {str(e)}"


def run_lintr_on_file(filepath: str, linters: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Run lintr on a single R file.
    
    Args:
        filepath: Path to the R file to analyze
        linters: Optional list of specific linters to use. If None, uses default linters.
    
    Returns:
        Dictionary containing lintr results, or None if lintr failed or file is invalid
    """
    if not os.path.isfile(filepath):
        return None
    
    # Check if file is an R file
    if not filepath.lower().endswith(('.r', '.R', '.Rmd')):
        return None
    
    try:
        # Normalize file path for R (handle Windows paths and escape quotes)
        normalized_path = filepath.replace('\\', '/').replace('"', '\\"')
        
        # Create R script to run lintr
        r_script = f"""
        # Load required libraries
        if (!requireNamespace("lintr", quietly = TRUE)) {{
            stop("lintr package is not installed")
        }}
        library(lintr)
        
        # Check if jsonlite is available (lintr dependency, but check anyway)
        has_jsonlite <- requireNamespace("jsonlite", quietly = TRUE)
        if (!has_jsonlite) {{
            # Try to install jsonlite if not available
            tryCatch({{
                install.packages("jsonlite", repos = "https://cloud.r-project.org", quiet = TRUE)
                has_jsonlite <- requireNamespace("jsonlite", quietly = TRUE)
            }}, error = function(e) {{}})
        }}
        
        # Read the file
        file_path <- "{normalized_path}"
        
        # Configure linters (use default if none specified)
        linter_config <- linters_with_defaults()
        
        # Run lintr
        lints <- tryCatch({{
            lint(file_path, linters = linter_config)
        }}, error = function(e) {{
            list()
        }})
        
        # Convert to JSON
        if (length(lints) > 0) {{
            result <- list(
                file = file_path,
                lints = lapply(lints, function(lint) {{
                    list(
                        line_number = as.integer(lint$line_number),
                        column_number = as.integer(lint$column_number),
                        type = as.character(lint$type),
                        message = as.character(lint$message),
                        line = as.character(lint$line),
                        linter = as.character(lint$linter)
                    )
                }}),
                total_lints = length(lints)
            )
        }} else {{
            result <- list(
                file = file_path,
                lints = list(),
                total_lints = 0L
            )
        }}
        
        # Output as JSON (jsonlite should be available as lintr dependency)
        if (has_jsonlite) {{
            cat(jsonlite::toJSON(result, auto_unbox = TRUE, pretty = FALSE))
        }} else {{
            # If jsonlite is not available, return minimal structure
            # This should rarely happen as lintr depends on jsonlite
            cat('{{"file":"', file_path, '","total_lints":', length(lints), ',"lints":[]}}', sep='')
        }}
        """
        
        # Run R script
        result = subprocess.run(
            ["Rscript", "--vanilla", "-e", r_script],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(filepath) or "."
        )
        
        if result.returncode != 0:
            # lintr might not be installed or there was an error
            return None
        
        # Parse JSON output
        try:
            output = result.stdout.strip()
            if not output:
                return None
            
            # Remove any warnings or messages before JSON
            # Find the JSON part (starts with {)
            json_start = output.find('{')
            if json_start == -1:
                return None
            
            json_output = output[json_start:]
            lintr_result = json.loads(json_output)
            return lintr_result
        except json.JSONDecodeError:
            return None
            
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        return None


def run_lintr_on_directory(directory: str, linters: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run lintr on all R files in a directory.
    
    Args:
        directory: Path to the directory containing R files
        linters: Optional list of specific linters to use. If None, uses default linters.
    
    Returns:
        Dictionary containing lintr results for all files
    """
    results = {
        "directory": directory,
        "files": [],
        "total_lints": 0,
        "total_files": 0,
        "files_with_lints": 0
    }
    
    r_extensions = [".r", ".R", ".Rmd"]
    
    for root, _, files in os.walk(directory):
        # Skip common directories
        if any(skip in root for skip in [".git", "node_modules", "__pycache__", ".Rproj.user"]):
            continue
        
        for file in files:
            if any(file.endswith(ext) for ext in r_extensions):
                filepath = os.path.join(root, file)
                file_result = run_lintr_on_file(filepath, linters)
                
                if file_result:
                    results["files"].append(file_result)
                    results["total_lints"] += file_result.get("total_lints", 0)
                    results["total_files"] += 1
                    if file_result.get("total_lints", 0) > 0:
                        results["files_with_lints"] += 1
    
    return results


def parse_lintr_results(lintr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and summarize lintr results into a structured format.
    
    Args:
        lintr_result: Raw lintr result dictionary
    
    Returns:
        Parsed and summarized lintr results
    """
    if not lintr_result:
        return {
            "total_lints": 0,
            "by_type": {},
            "by_linter": {},
            "files_analyzed": 0,
            "files_with_lints": 0
        }
    
    summary = {
        "total_lints": 0,
        "by_type": {},  # error, warning, style, etc.
        "by_linter": {},  # which linter found the issue
        "files_analyzed": 0,
        "files_with_lints": 0,
        "file_details": []
    }
    
    # Handle single file result
    if "lints" in lintr_result and "file" in lintr_result:
        # Single file result
        files_data = [lintr_result]
    elif "files" in lintr_result:
        # Directory result
        files_data = lintr_result.get("files", [])
    else:
        files_data = []
    
    for file_data in files_data:
        file_path = file_data.get("file", "")
        lints = file_data.get("lints", [])
        total_lints = file_data.get("total_lints", len(lints))
        
        summary["files_analyzed"] += 1
        summary["total_lints"] += total_lints
        
        if total_lints > 0:
            summary["files_with_lints"] += 1
        
        file_detail = {
            "file": file_path,
            "total_lints": total_lints,
            "by_type": {},
            "by_linter": {}
        }
        
        for lint in lints:
            lint_type = lint.get("type", "unknown")
            linter_name = lint.get("linter", "unknown")
            
            # Count by type
            summary["by_type"][lint_type] = summary["by_type"].get(lint_type, 0) + 1
            file_detail["by_type"][lint_type] = file_detail["by_type"].get(lint_type, 0) + 1
            
            # Count by linter
            summary["by_linter"][linter_name] = summary["by_linter"].get(linter_name, 0) + 1
            file_detail["by_linter"][linter_name] = file_detail["by_linter"].get(linter_name, 0) + 1
        
        if total_lints > 0:
            summary["file_details"].append(file_detail)
    
    return summary


def get_lintr_summary_for_file(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Get a summary of lintr results for a single file.
    
    Args:
        filepath: Path to the R file
    
    Returns:
        Summary dictionary with lintr metrics, or None if lintr is unavailable
    """
    is_available, error = check_lintr_available(install_if_missing=True)
    if not is_available:
        return None
    
    lintr_result = run_lintr_on_file(filepath)
    if lintr_result is None:
        return None
    
    summary = parse_lintr_results(lintr_result)
    
    # Add file-specific summary
    return {
        "file": filepath,
        "total_lints": summary.get("total_lints", 0),
        "by_type": summary.get("by_type", {}),
        "by_linter": summary.get("by_linter", {}),
        "has_lints": summary.get("total_lints", 0) > 0
    }


def get_lintr_summary_for_repo(repo_path: str) -> Optional[Dict[str, Any]]:
    """
    Get a summary of lintr results for an entire repository.
    
    Args:
        repo_path: Path to the repository directory
    
    Returns:
        Summary dictionary with lintr metrics for the repository, or None if lintr is unavailable
    """
    is_available, error = check_lintr_available(install_if_missing=True)
    if not is_available:
        return None
    
    lintr_result = run_lintr_on_directory(repo_path)
    if not lintr_result:
        return None
    
    summary = parse_lintr_results(lintr_result)
    
    # Add repository-level summary
    return {
        "repo": repo_path,
        "total_lints": summary.get("total_lints", 0),
        "total_files": summary.get("files_analyzed", 0),
        "files_with_lints": summary.get("files_with_lints", 0),
        "by_type": summary.get("by_type", {}),
        "by_linter": summary.get("by_linter", {}),
        "file_details": summary.get("file_details", [])
    }

