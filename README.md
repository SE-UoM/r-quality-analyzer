# r-quality-analyzer

`r-quality-analyzer` is a Python toolkit for reviewing the structural quality of R projects. It parses every `.R`, `.r`, and `.Rmd` file, computes a set of classic metrics, and emits JSON summaries that can be used in QA pipelines, dashboards, or reports. The library exposes both a friendly CLI and composable Python APIs, so you can automate repository checks, inspect a single file, or embed the analyzers inside larger tooling.

---

## Highlights

- Analyzes R files for LOC, number of functions, cyclomatic complexity, methods-per-class, coupling between objects, lack of cohesion, and paradigm tendencies.
- Works on local folders or GitHub repositories (short `user/repo` syntax or full URLs). Optional cloning is handled automatically via GitPython.
- Produces machine-friendly JSON reports that include both per-file and repository-level aggregates.
- Provides both CLI (`r-quality-analyzer ...`) and Python helpers (`analyzer.analyze_file`, `analyzer.analyze_repo`).
- Allows custom metric stacks by passing your own `Metric` implementations into `FileAnalyzer`.

---

## Installation

```bash
pip install r-quality-analyzer
```

The only non-standard dependency is [GitPython](https://gitpython.readthedocs.io/), used for cloning remote repositories. If you only run the analyzer on local directories or single files, Git is optional.

For local development:

```bash
git clone https://github.com/<you>/r-quality-analyzer
cd r-quality-analyzer
pip install -e ".[dev]"  # or simply pip install -e .
```

---

## CLI quick start

The package exposes the `r-quality-analyzer` executable (see `pyproject.toml` entry points). Run `--help` to explore all options.

```bash
r-quality-analyzer --help
```

### Analyze a local repository

```bash
r-quality-analyzer path/to/local/repo
```

### Analyze a GitHub repo (clone + clean up)

```bash
r-quality-analyzer repos/greekonomics
# or
r-quality-analyzer https://github.com/AMantes/Greekonomics
```

Pass `--keep-clone` if you would like to inspect the temporary checkout.

### Analyze a single file

```bash
r-quality-analyzer --file path/to/script.R
```

### Persist the report to disk

```bash
r-quality-analyzer my/local/repo -o report.json
r-quality-analyzer https://github.com/AMantes/Greekonomics --o report.json
```

The CLI always prints JSON; when `-o/--output` is set, the same payload is also written to the provided path.

---

## Python API quick start

Use the thin compatibility module (`r_quality_analyzer.analyzer`) to integrate with existing automation:

```python
from r_quality_analyzer import analyzer

# Analyze a single R file
file_report = analyzer.analyze_file("src/example.R")
print(file_report["loc"], file_report["cc_avg"])

# Analyze a repository (local folder or previously cloned checkout)
repo_report = analyzer.analyze_repo("./path/to/repo")
print(repo_report["total_loc"], len(repo_report["files"]))
```

For more control, instantiate the core classes directly:

```python
from r_quality_analyzer.domain.file_analyzer import FileAnalyzer
from r_quality_analyzer.domain.repository_analyzer import RepositoryAnalyzer
from r_quality_analyzer.infrastructure.repositories import LocalRepositorySource

custom_file_analyzer = FileAnalyzer()
source = LocalRepositorySource("./repo")
repo_report = RepositoryAnalyzer(source, custom_file_analyzer).analyze().to_dict()
```

---

## Metrics reference

| Metric | Key | Description |
| --- | --- | --- |
| Lines of code | `loc` | Counts non-empty, non-comment lines. |
| Number of functions | `nom` | Total R functions detected in the file. |
| Cyclomatic complexity | `cc_avg`, `cc_max` | Per-function complexity estimate; output contains average and maximum values. |
| Methods per class | `mpc` | Average number of methods per detected class. |
| Coupling between objects | `cbo` | Simple count of inter-function call relationships. |
| Lack of cohesion | `lcom` | Heuristic cohesion measure across functions/classes. |
| Paradigm detector | `paradigm`, `paradigm_distribution` | Labels files (functional, oop, mixed) and aggregates repository-wide distribution. |

All metrics are implemented in `r_quality_analyzer/domain/metrics/`. Each metric returns a `MetricResult`, so you can add new metrics by subclassing `Metric` and injecting them into `FileAnalyzer`.

```python
from r_quality_analyzer.domain.metrics import Metric, MetricResult

class CommentDensityMetric(Metric):
    name = "comment_density"

    def compute(self, parsed_file):
        density = parsed_file.comment_lines / max(parsed_file.total_lines, 1)
        return MetricResult(self.name, density)

custom_analyzer = FileAnalyzer(metrics=[CommentDensityMetric()])
```

---

## Report structure

Repository reports contain an aggregate section plus the list of per-file metrics. Example (truncated):

```json
{
  "repo": "https://github.com/tidyverse/ggplot2",
  "repo_name": "ggplot2",
  "local_repo": "/tmp/r_quality_analyzer_xxx",
  "total_files": 42,
  "total_loc": 8123,
  "total_nom": 296,
  "avg_cc": 3.87,
  "avg_mpc": 1.4,
  "total_cbo": 91,
  "avg_lcom": 0.42,
  "paradigm": "mixed",
  "paradigm_distribution": {"functional": 25, "oop": 10, "mixed": 7},
  "total_classes": 18,
  "files": [
    {
      "file": "R/foo.R",
      "loc": 120,
      "nom": 4,
      "cc_avg": 2.75,
      "cc_max": 4,
      "mpc": 0,
      "cbo": 3,
      "lcom": 0.32,
      "paradigm": "functional",
      "num_classes": 0
    }
    // ...
  ]
}
```

When analyzing a single file, the CLI wraps the metrics in `{ "file": { ... }, "single_file": true }`.

---

## Working with repositories

- **Local directories**: validated with `os.path.isdir`; ensure the path exists.
- **GitHub repos**: accept `user/repo`, HTTPS URLs, and `git@github.com:user/repo`. By default the temporary clone is removed; pass `--keep-clone` to leave it on disk.
- **Supported files**: `.r`, `.R`, and `.Rmd`. Directories such as `.git`, `node_modules`, `__pycache__`, `.Rproj.user` are skipped automatically.

---

## Contributing & development

1. Clone and install dependencies (see *Installation*).
2. Run tests with `pytest`.
3. Format / lint according to your preferred tooling (the repository avoids strict formatters).
4. Open a pull request describing the change and include sample reports when relevant.

Bug reports and feature requests are welcome! Please include sample R files or repositories to help reproduce issues.

---

## License

MIT License © r-quality-analyzer contributors.


