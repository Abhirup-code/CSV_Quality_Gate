# Changelog

All notable changes to CSV Quality Gate. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.3.1] - 2026-10-31

### Changed
- The GitHub Action's display name is now "Data Quality Gate for CSV", because the Marketplace
  needs a unique name. Workflows that use the Action do not change.

## [1.3.0] - 2026-10-31

### Added
- Check several files with the same rules in one run, each with its own report folder; `--junit` writes
  one test suite per file.
- `--delimiter` for semicolon, tab, and pipe separated files, in checks, inference, quarantine, and the
  GitHub Action.
- `min` and `max` for date columns, and `"max": "today"` to catch dates in the future.
- `max_blank_rate`, a limit on how much of a column may be blank.

### Fixed
- Files saved by Excel as "CSV UTF-8" start with an invisible byte-order mark, which made the first
  column look missing. They are now read correctly.
- A rules file with a text bound such as `"min": "5"` on a number column crashed the check. It is now
  rejected with a clear message when the rules load.

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
- Licensed under the Apache License 2.0 (`LICENSE` and `NOTICE`).

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
