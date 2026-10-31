"""Command line interface. Exit codes: 0 pass, 1 data quality failure, 2 usage error."""
import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checks import read_csv, run_checks
from .infer import infer_rules
from .quarantine import write_quarantine
from .report import summarize, to_html, to_junit_files, to_markdown
from .rules import RulesError, load_rules


def percentage(text):
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a number") from None
    if not 0 <= value <= 100:
        raise argparse.ArgumentTypeError("must be between 0 and 100")
    return value


def delimiter(text):
    """One character, with names for the ones that are awkward to type in a shell."""
    value = {"tab": "\t", "\\t": "\t", "semicolon": ";", "comma": ",", "pipe": "|"}.get(text, text)
    if len(value) != 1 or value in "\r\n\"":
        raise argparse.ArgumentTypeError("must be one character, or tab, semicolon, comma, or pipe")
    return value


DELIMITER_HELP = "field separator: one character, or tab, semicolon, comma, or pipe (default: comma)"


def build_parser():
    p = argparse.ArgumentParser(prog="qualitygate", description="Check a CSV file against data quality rules.",
                                epilog="To draft a rules file from a good CSV: qualitygate infer FILE.csv")
    p.add_argument("csv_paths", nargs="+", metavar="csv_path",
                   help="CSV file to check; give several to check them all with the same rules")
    p.add_argument("--rules", required=True, help="JSON rules file")
    p.add_argument("--delimiter", type=delimiter, default=",", help=DELIMITER_HELP)
    p.add_argument("--out", default="reports", help="folder for report.json, report.md, and report.html")
    p.add_argument("--fail-on-warning", action="store_true", help="exit 1 if there are warnings too")
    p.add_argument("--max-error-rate", type=percentage, metavar="PERCENT",
                   help="pass if at most this percentage of rows have errors (file-wide errors still fail)")
    p.add_argument("--quarantine", metavar="FOLDER",
                   help="also write passed.csv (rows with no errors) and failed.csv (the rest, with reasons)")
    p.add_argument("--junit", metavar="FILE", help="also write a JUnit XML test report for CI")
    p.add_argument("--version", action="version", version=f"qualitygate {__version__}")
    return p


def build_infer_parser():
    p = argparse.ArgumentParser(prog="qualitygate infer",
                                description="Draft a rules file from a CSV that is known to be good.")
    p.add_argument("csv_path", help="a clean CSV file to learn from")
    p.add_argument("--out", help="write the rules here instead of printing them")
    p.add_argument("--name", help="rules name (default: the file name)")
    p.add_argument("--delimiter", type=delimiter, default=",", help=DELIMITER_HELP)
    return p


def infer_main(argv):
    args = build_infer_parser().parse_args(argv)
    try:
        header, rows = read_csv(args.csv_path, args.delimiter)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rules = infer_rules(header, rows, name=args.name or Path(args.csv_path).stem)
    text = json.dumps(rules, indent=2) + "\n"
    if args.out:
        try:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote draft rules for {len(rules['columns'])} columns to {args.out}. Review them before use.",
              file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def folder_names(paths):
    """One report folder per file, named after the file; a repeated name gets a number."""
    names, used = [], set()
    for path in paths:
        stem = Path(path).stem or "file"
        name, n = stem, 1
        while name in used:
            n += 1
            name = f"{stem}-{n}"
        used.add(name)
        names.append(name)
    return names


def check_file(path, rules, rules_name, args, out, quarantine):
    """Check one file and write its reports. Returns (exit code, summary, issues), or (2, None, None)."""
    try:
        header, rows = read_csv(path, args.delimiter)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2, None, None

    issues = run_checks(header, rows, rules)
    summary = summarize(issues, len(rows), source=Path(path).name, rules_name=rules_name,
                        max_error_rate=args.max_error_rate)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps({"summary": summary, "issues": issues}, indent=2))
    (out / "report.md").write_text(to_markdown(summary, issues))
    (out / "report.html").write_text(to_html(summary, issues), encoding="utf-8")

    print(f"{summary['status']}: {summary['total_rows']} rows, "
          f"{summary['errors']} errors, {summary['warnings']} warnings "
          f"(row pass rate {summary['row_pass_rate']}%). Reports in {out}/")
    if quarantine:
        good, bad = write_quarantine(quarantine, header, rows, issues, args.delimiter)
        print(f"Quarantine: {good} rows in passed.csv, {bad} rows in failed.csv ({quarantine}/)")

    failed = summary["status"] == "FAIL" or (args.fail_on_warning and summary["warnings"])
    return (1 if failed else 0), summary, issues


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["infer"]:
        return infer_main(argv[1:])
    args = build_parser().parse_args(argv)
    try:
        rules = load_rules(args.rules)
    except (RulesError, OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rules_name = rules.get("name", Path(args.rules).stem)

    # One file keeps the simple layout; several get a subfolder each, named after the file.
    several = len(args.csv_paths) > 1
    names = folder_names(args.csv_paths)
    codes, results = [], []
    for path, name in zip(args.csv_paths, names, strict=True):
        out = Path(args.out) / name if several else Path(args.out)
        quarantine = args.quarantine and (Path(args.quarantine) / name if several else Path(args.quarantine))
        if several:
            print(f"{path}:")
        code, summary, issues = check_file(path, rules, rules_name, args, out, quarantine)
        codes.append(code)
        if summary is not None:
            results.append((summary, issues))

    if args.junit and results:
        Path(args.junit).parent.mkdir(parents=True, exist_ok=True)
        Path(args.junit).write_text(to_junit_files(results, rules["columns"]), encoding="utf-8")
    if several:
        passed = codes.count(0)
        print(f"{passed} of {len(codes)} files passed.")
    return max(codes)


if __name__ == "__main__":
    sys.exit(main())
