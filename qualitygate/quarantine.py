"""Split a checked file into rows that passed and rows that failed, so a pipeline can load the good
rows and hold the bad ones back for review."""
import csv
from pathlib import Path


def split_rows(rows, issues):
    """(passed, failed) where failed rows carry a summary of their errors. Warnings do not fail a row."""
    problems = {}
    for issue in issues:
        if issue["severity"] == "error" and issue["row"] is not None:
            where = f"{issue['column']}: " if issue["column"] else ""
            problems.setdefault(issue["row"], []).append(where + issue["message"])
    passed = [cells for line, cells in rows if line not in problems]
    failed = [(line, cells, "; ".join(problems[line])) for line, cells in rows if line in problems]
    return passed, failed


def write_quarantine(folder, header, rows, issues, delimiter=","):
    """Write passed.csv and failed.csv into folder and return (passed count, failed count)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    passed, failed = split_rows(rows, issues)
    with open(folder / "passed.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(passed)
    with open(folder / "failed.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["_line", "_errors", *header])
        for line, cells, errors in failed:
            writer.writerow([line, errors, *cells])
    return len(passed), len(failed)
