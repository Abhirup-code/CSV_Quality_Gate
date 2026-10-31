# Changelog

All notable changes to CSV Quality Gate. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-10-31

### Added
- `pip install .` gives a `qualitygate` command.
- `--max-error-rate PERCENT` passes a run when at most that share of rows have errors. File-wide errors
  still fail.
- `compare` dataset rules check two columns in the same row, like `ship_date >= order_date`, using each
  column's type.
- `report.html`, a self-contained report with summary cards and example issues, in light or dark mode.
- A reusable GitHub Action (`action.yml`) that fails on bad data, writes the report into the job summary,
  and sets `status`, `errors`, and `row-pass-rate` outputs. CI tests the action itself.
- ruff linting in CI, including security rules.

## [1.1.0] - 2026-10-30

### Added
- `qualitygate infer FILE.csv` drafts a rules file from a known-good CSV: types, required, unique,
  never-negative numbers, and short lists of allowed values.
- `--quarantine FOLDER` writes `passed.csv` and `failed.csv`, so a pipeline can load the good rows and
  hold back the rest with their line numbers and error reasons.
- `--junit FILE` writes a JUnit XML test report that GitHub Actions, Jenkins, and Azure DevOps display.
- `--version`.
- Property-based tests with Hypothesis: any file passes the rules inferred from it, and summary counts
  always add up.

### Fixed
- `infer --out` into a folder that did not exist raised an unhandled error.

### Security
- CI runs with a read-only token, without stored checkout credentials, and with every action pinned to a
  commit SHA.

## [1.0.0] - 2026-10-11

### Added
- Rules-driven checks for CSV files (type, required, range, allowed values, pattern, length, unique,
  severity), dataset checks, JSON and Markdown reports, and exit codes for CI.
