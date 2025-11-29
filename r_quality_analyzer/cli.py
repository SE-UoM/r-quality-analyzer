"""
CLI interface for R Quality Analyzer
"""

import os
import sys
import json
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


def clone_github_repo(repo_url: str, target_dir: Optional[str] = None) -> str:
    """
    Clone a GitHub repository to a temporary directory.
    
    Args:
        repo_url: GitHub repository URL (e.g., 'https://github.com/user/repo' or 'user/repo')
        target_dir: Optional target directory. If None, creates a temp directory.
    
    Returns:
        Path to the cloned repository
    """
    if not GIT_AVAILABLE:
        raise ImportError(
            "GitPython is required for cloning repositories. "
            "Install it with: pip install gitpython"
        )
    
    # Normalize repo URL
    if not repo_url.startswith(('http://', 'https://', 'git@')):
        if '/' in repo_url:
            repo_url = f"https://github.com/{repo_url}.git"
        else:
            raise ValueError(f"Invalid repository URL: {repo_url}")
    elif not repo_url.endswith('.git'):
        repo_url = f"{repo_url}.git"
    
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix="r_quality_analyzer_")
    else:
        os.makedirs(target_dir, exist_ok=True)
    
    print(f"Cloning repository: {repo_url}")
    Repo.clone_from(repo_url, target_dir)
    print(f"Repository cloned to: {target_dir}")
    
    return target_dir


def is_github_url(path: str) -> bool:
    """Check if the path is a GitHub repository URL."""
    return (
        path.startswith('http://github.com/') or
        path.startswith('https://github.com/') or
        path.startswith('git@github.com:') or
        ('github.com' in path and '/' in path and not os.path.exists(path))
    )


def is_github_repo_format(path: str) -> bool:
    """Check if path is in format 'user/repo'."""
    parts = path.split('/')
    return len(parts) == 2 and not os.path.exists(path) and not path.startswith('http')


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze R code quality metrics for a repository or folder"
    )
    parser.add_argument(
        "target",
        help="GitHub repository URL (e.g., 'user/repo' or 'https://github.com/user/repo') or local folder path"
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
        help="Keep cloned repository after analysis (only for GitHub repos)",
        action="store_true"
    )
    
    args = parser.parse_args()
    
    target = args.target
    temp_dir = None
    cleanup_needed = False
    
    try:
        # Determine if we need to clone a GitHub repo
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
            if is_github_url(target) or is_github_repo_format(target):
                # Clone GitHub repository
                if not GIT_AVAILABLE:
                    print(
                        "Error: GitPython is required for cloning repositories.\n"
                        "Install it with: pip install gitpython",
                        file=sys.stderr
                    )
                    sys.exit(1)
                
                temp_dir = clone_github_repo(target)
                cleanup_needed = not args.keep_clone
                repo_path = temp_dir
            else:
                # Local folder
                if not os.path.isdir(target):
                    print(f"Error: Directory not found: {target}", file=sys.stderr)
                    sys.exit(1)
                repo_path = target
            
            # Analyze repository
            # Determine repo URL if it was a GitHub repo
            repo_url = None
            if is_github_url(target) or is_github_repo_format(target):
                # Normalize the target to a proper URL
                if not target.startswith(('http://', 'https://', 'git@')):
                    repo_url = f"https://github.com/{target}"
                else:
                    repo_url = target.rstrip('.git')
            
            output_data = analyze_repo(repo_path, repo_url=repo_url)
        
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



