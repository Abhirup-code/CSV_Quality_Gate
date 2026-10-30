# Changelog

All notable changes to CSV Quality Gate. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

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
