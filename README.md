# R Quality Analyzer

A Python library and CLI tool for analyzing R code quality metrics. This tool can analyze both local R projects and remote Git repositories (GitHub, GitLab, Bitbucket, etc.). **Supports both functional and object-oriented R code** (S3, S4, R6, and Reference Classes).

## Installation

### Install from GitHub

Install directly from GitHub using pip:

```bash
pip install git+https://github.com/yourusername/r-quality-analyzer.git
```

Replace `yourusername` with your actual GitHub username.

### Install from Local Source

Clone and install locally:

```bash
git clone https://github.com/yourusername/r-quality-analyzer.git
cd r-quality-analyzer
pip install .
```

### Development Installation

For development, install in editable mode:

```bash
pip install -e .
```

## Metrics

The analyzer calculates the following metrics:

- **file**: Path to the analyzed file
- **loc**: Lines of Code (excluding comments and blank lines)
- **nom**: Number of Methods/Functions
- **cc_avg**: Average Cyclomatic Complexity
- **mpc**: Methods Per Class (for OOP: average methods per class; for functional: ratio of method calls to functions)
- **cbo**: Coupling Between Objects (number of package dependencies)
- **lcom**: Lack of Cohesion of Methods
- **paradigm**: Code paradigm detected: `"functional"`, `"oop"`, or `"mixed"`
- **classes** (OOP only): Dictionary of class names and their method counts
- **num_classes** (OOP only): Total number of classes detected

The analyzer automatically detects and handles:
- **Functional R code**: Standard function definitions
- **S3 methods**: Functions with dot notation (e.g., `print.myclass`)
- **S4 classes**: Classes defined with `setClass()` and methods with `setMethod()`
- **R6 classes**: Modern OOP classes defined with `R6Class()`
- **Reference Classes**: Classes defined with `setRefClass()`

## Usage

### Command Line Interface

#### Analyze a local folder:

```bash
r-quality-analyzer /path/to/r/project
```

#### Analyze a Git repository:

```bash
# GitHub (shorthand format)
r-quality-analyzer user/repo

# GitHub (full URL)
r-quality-analyzer https://github.com/user/repo

# GitLab
r-quality-analyzer https://gitlab.com/user/repo

# Bitbucket
r-quality-analyzer https://bitbucket.org/user/repo

# SSH format
r-quality-analyzer git@github.com:user/repo.git
```

#### Analyze a single file:

```bash
r-quality-analyzer -f /path/to/file.R
```

#### Save results to a file:

```bash
r-quality-analyzer user/repo -o results.json
```

#### Keep cloned repository after analysis:

```bash
r-quality-analyzer user/repo --keep-clone
```

### Python API

```python
from r_quality_analyzer import analyze_file, analyze_repo

# Analyze a single file
metrics = analyze_file("path/to/file.R")
print(metrics)

# Analyze a repository
results = analyze_repo("path/to/r/project")
print(results)
```

## Requirements

- Python 3.7+
- GitPython (for Git repository cloning)

## Output Example
```json
{
  "repo": "https://github.com/AMantes/Greekonomics",
  "repo_name": "Greekonomics",
  "local_repo": "local\\path\\r_quality_analyzer_lma0y3bn",
  "total_files": 2,
  "total_loc": 1889,
  "total_nom": 30,
  "avg_cc": 1.98,
  "avg_mpc": 13.33,
  "total_cbo": 4,
  "avg_lcom": 62.0,
  "paradigm": "functional",
  "paradigm_distribution": {
    "functional": 2
  },
  "total_classes": 0,
  "files": [
    {
      "loc": 782,
      "nom": 9,
      "cc_avg": 1.78,
      "complexities": [
        {
          "function": "theme_greekonomics",
          "start_line": 32,
          "cc": 1
        },
        ...
      ],
      "mpc": 8.56,
      "cbo": 2,
      "lcom": 7,
      "paradigm": "functional",
      "classes": {},
      "num_classes": 0,
      "file": "C:\\Users\\User\\AppData\\Local\\Temp\\r_quality_analyzer_lma0y3bn\\Greekonomics_51_public.R"
    },
    ...
  ]
}
```

## License

MIT License

