"""Command line interface. Exit codes: 0 pass, 1 data quality failure, 2 usage error."""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checks import read_csv, run_checks
from .report import summarize, to_markdown
from .rules import RulesError, load_rules


def build_parser():
    p = argparse.ArgumentParser(prog="qualitygate", description="Check a CSV file against data quality rules.")
    p.add_argument("csv_path", help="CSV file to check")
    p.add_argument("--rules", required=True, help="JSON rules file")
    p.add_argument("--out", default="reports", help="folder for report.json and report.md")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--fail-on-warning", action="store_true", help="exit 1 if there are warnings too")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)
        header, rows = read_csv(args.csv_path)
    except (RulesError, OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    issues = run_checks(header, rows, rules)
    summary = summarize(issues, len(rows), source=Path(args.csv_path).name,
                        rules_name=rules.get("name", Path(args.rules).stem))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps({"summary": summary, "issues": issues}, indent=2))
    (out / "report.md").write_text(to_markdown(summary, issues))

    print(f"{summary['status']}: {summary['total_rows']} rows, "
          f"{summary['errors']} errors, {summary['warnings']} warnings "
          f"(row pass rate {summary['row_pass_rate']}%). Reports in {out}/")

    if summary["errors"] or (args.fail_on_warning and summary["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
