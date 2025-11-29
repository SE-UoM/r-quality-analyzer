"""
CLI interface for R Quality Analyzer
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional

try:
    from git import Repo
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False

from .analyzer import analyze_repo, analyze_file

# Check for lintr availability
try:
    from .lintr_analyzer import check_lintr_available
    LINTR_CHECK_AVAILABLE = True
except ImportError:
    LINTR_CHECK_AVAILABLE = False
    check_lintr_available = None


def clone_repo(repo_url: str, target_dir: Optional[str] = None) -> str:
    """
    Clone a Git repository to a temporary directory.
    
    Args:
        repo_url: Git repository URL (e.g., 'https://github.com/user/repo', 
                 'git@github.com:user/repo.git', 'https://gitlab.com/user/repo', etc.)
        target_dir: Optional target directory. If None, creates a temp directory.
    
    Returns:
        Path to the cloned repository
    """
    if not GIT_AVAILABLE:
        raise ImportError(
            "GitPython is required for cloning repositories. "
            "Install it with: pip install gitpython"
        )
    
    # Normalize repo URL - ensure it ends with .git if it's an HTTP/HTTPS URL
    if repo_url.startswith(('http://', 'https://')):
        if not repo_url.endswith('.git'):
            repo_url = f"{repo_url}.git"
    # For SSH URLs (git@...), keep as is
    elif not repo_url.startswith('git@'):
        # If it's not a full URL and not a local path, assume it might be a shorthand
        # But we'll let GitPython handle validation
        if '/' in repo_url and not os.path.exists(repo_url):
            # Try to detect if it's a GitHub shorthand (user/repo)
            # For other services, user needs to provide full URL
            if not any(domain in repo_url for domain in ['http', 'git@', '.com', '.org', '.io']):
                # Assume GitHub shorthand for backward compatibility
                repo_url = f"https://github.com/{repo_url}.git"
    
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="r_quality_analyzer_")
    else:
        os.makedirs(target_dir, exist_ok=True)
    
    print(f"Cloning repository: {repo_url}")
    Repo.clone_from(repo_url, target_dir)
    print(f"Repository cloned to: {target_dir}")
    
    return target_dir


def is_git_url(path: str) -> bool:
    """
    Check if the path is a Git repository URL.
    
    Supports:
    - HTTP/HTTPS URLs (https://github.com/user/repo, https://gitlab.com/user/repo, etc.)
    - SSH URLs (git@github.com:user/repo.git, git@gitlab.com:user/repo.git, etc.)
    - Shorthand format (user/repo) - assumed to be GitHub for backward compatibility
    """
    # Check if it's a full URL
    if path.startswith(('http://', 'https://', 'git@')):
        return True
    
    # Check if it contains common Git hosting domains
    git_domains = ['github.com', 'gitlab.com', 'bitbucket.org', 'sourceforge.net', 
                   'gitea.com', 'codeberg.org', 'git.sr.ht']
    if any(domain in path for domain in git_domains):
        return not os.path.exists(path)
    
    # Check if it's a shorthand format (user/repo) and not a local path
    parts = path.split('/')
    if len(parts) == 2 and not os.path.exists(path) and not path.startswith('http'):
        return True
    
    return False


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze R code quality metrics for a repository or folder"
    )
    parser.add_argument(
        "target",
        help="Git repository URL (e.g., 'https://github.com/user/repo', 'https://gitlab.com/user/repo', 'git@github.com:user/repo.git', 'user/repo') or local folder path"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file path for JSON results (default: stdout)",
        default=None
    )
    parser.add_argument(
        "-f", "--file",
        help="Analyze a single file instead of a repository",
        action="store_true"
    )
    parser.add_argument(
        "--keep-clone",
        help="Keep cloned repository after analysis (only for remote Git repos)",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    target = args.target
    temp_dir = None
    cleanup_needed = False
    
    try:
        # Determine if we need to clone a Git repo
        if args.file:
            # Single file analysis
            if not os.path.isfile(target):
                print(f"Error: File not found: {target}", file=sys.stderr)
                sys.exit(1)
            
            from .analyzer import analyze_file
            result = analyze_file(target)
            if result is None:
                print(f"Error: Could not analyze file: {target}", file=sys.stderr)
                sys.exit(1)
            
            # Format as single file result
            output_data = {
                "file": result,
                "single_file": True
            }
        else:
            # Repository or folder analysis
            if is_git_url(target):
                # Clone Git repository
                if not GIT_AVAILABLE:
                    print(
                        "Error: GitPython is required for cloning repositories.\n"
                        "Install it with: pip install gitpython",
                        file=sys.stderr
                    )
                    sys.exit(1)
                
                temp_dir = clone_repo(target)
                cleanup_needed = not args.keep_clone
                repo_path = temp_dir
            else:
                # Local folder
                if not os.path.isdir(target):
                    print(f"Error: Directory not found: {target}", file=sys.stderr)
                    sys.exit(1)
                repo_path = target
            
            # Analyze repository
            # Determine repo URL if it was a remote Git repo
            repo_url = None
            if is_git_url(target):
                # Normalize the target to a proper URL
                if target.startswith(('http://', 'https://', 'git@')):
                    repo_url = target.rstrip('.git')
                else:
                    # Shorthand format - assume GitHub for backward compatibility
                    repo_url = f"https://github.com/{target}"
            
            output_data = analyze_repo(repo_path, repo_url=repo_url)
        
        # Check lintr availability and try to install if missing
        if LINTR_CHECK_AVAILABLE and check_lintr_available:
            # Check if lintr needs to be installed (quick check before attempting install)
            try:
                from .lintr_analyzer import check_r_available
                r_available, r_error = check_r_available()
                
                if not r_available:
                    if not args.output:  # Only show warning if outputting to stdout
                        print(
                            f"\n⚠️  R is not installed: {r_error}\n"
                            "   Lintr analysis requires R to be installed.\n"
                            "   Install R from: https://cran.r-project.org/\n"
                            "   After installing R, lintr will be automatically installed on next run.\n"
                            "   Analysis will continue without lintr results.\n",
                            file=sys.stderr
                        )
                else:
                    # R is available, check if lintr needs installation
                    r_check_script = """
                    if (!requireNamespace("lintr", quietly = TRUE)) {
                        quit(status = 1, save = "no")
                    }
                    quit(status = 0, save = "no")
                    """
                    needs_install = subprocess.run(
                        ["Rscript", "--vanilla", "-e", r_check_script],
                        capture_output=True,
                        timeout=5
                    ).returncode != 0
                    
                    if needs_install and not args.output:
                        print("Installing lintr R package (first time only, this may take a moment)...", file=sys.stderr)
            except Exception:
                pass  # Will be handled by check_lintr_available
            
            is_available, error_msg = check_lintr_available(install_if_missing=True)
            if not is_available:
                if not args.output and error_msg:  # Only show warning if outputting to stdout
                    # Don't show error if R is not installed (already shown above)
                    if "R is not installed" not in (error_msg or ""):
                        print(
                            f"\n⚠️  Lintr unavailable: {error_msg}\n"
                            "   Lintr results will not be included in the analysis.\n"
                            "   To install manually: Rscript -e \"install.packages('lintr', repos='https://cloud.r-project.org')\"\n",
                            file=sys.stderr
                        )
        
        # Output results
        json_output = json.dumps(output_data, indent=2)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Results saved to: {args.output}")
        else:
            print(json_output)
    
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Cleanup temporary directory if needed
        if cleanup_needed and temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up temporary directory: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()



