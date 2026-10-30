"""Command line interface. Exit codes: 0 pass, 1 data quality failure, 2 usage error."""
import argparse
import json
import sys
from pathlib import Path

from .checks import read_csv, run_checks
from .infer import infer_rules
from .quarantine import write_quarantine
from .report import summarize, to_markdown
from .rules import RulesError, load_rules


def build_parser():
    p = argparse.ArgumentParser(prog="qualitygate", description="Check a CSV file against data quality rules.",
                                epilog="To draft a rules file from a good CSV: qualitygate infer FILE.csv")
    p.add_argument("csv_path", help="CSV file to check")
    p.add_argument("--rules", required=True, help="JSON rules file")
    p.add_argument("--out", default="reports", help="folder for report.json and report.md")
    p.add_argument("--fail-on-warning", action="store_true", help="exit 1 if there are warnings too")
    p.add_argument("--quarantine", metavar="FOLDER",
                   help="also write passed.csv (rows with no errors) and failed.csv (the rest, with reasons)")
    return p


def build_infer_parser():
    p = argparse.ArgumentParser(prog="qualitygate infer",
                                description="Draft a rules file from a CSV that is known to be good.")
    p.add_argument("csv_path", help="a clean CSV file to learn from")
    p.add_argument("--out", help="write the rules here instead of printing them")
    p.add_argument("--name", help="rules name (default: the file name)")
    return p


def infer_main(argv):
    args = build_infer_parser().parse_args(argv)
    try:
        header, rows = read_csv(args.csv_path)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rules = infer_rules(header, rows, name=args.name or Path(args.csv_path).stem)
    text = json.dumps(rules, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text)
        print(f"Wrote draft rules for {len(rules['columns'])} columns to {args.out}. Review them before use.",
              file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["infer"]:
        return infer_main(argv[1:])
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
    if args.quarantine:
        good, bad = write_quarantine(args.quarantine, header, rows, issues)
        print(f"Quarantine: {good} rows in passed.csv, {bad} rows in failed.csv ({args.quarantine}/)")

    if summary["errors"] or (args.fail_on_warning and summary["warnings"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
