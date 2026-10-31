"""Summaries and report formats."""
import xml.etree.ElementTree as ET
from collections import Counter


def summarize(issues, total_rows, source="", rules_name="", max_error_rate=None):
    """Counts for a run. With max_error_rate (a percentage), row errors up to that share of rows are
    tolerated; file-wide errors such as a missing column always fail."""
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    bad_rows = {i["row"] for i in errors if i["row"] is not None}
    clean = total_rows - len(bad_rows)
    error_rate = round(100 * len(bad_rows) / total_rows, 1) if total_rows else 0.0
    file_errors = any(i["row"] is None for i in errors)
    if not errors:
        status = "PASS"
    elif max_error_rate is not None and not file_errors and 100 * len(bad_rows) <= max_error_rate * total_rows:
        status = "PASS"
    else:
        status = "FAIL"
    return {
        "source": source,
        "rules": rules_name,
        "status": status,
        "max_error_rate": max_error_rate,
        "row_error_rate": error_rate,
        "total_rows": total_rows,
        "rows_with_errors": len(bad_rows),
        "row_pass_rate": round(100 * clean / total_rows, 1) if total_rows else 100.0,
        "errors": len(errors),
        "warnings": len(warnings),
        "by_rule": dict(Counter(i["rule"] for i in issues)),
        "by_column": dict(Counter(i["column"] or "(dataset)" for i in issues)),
    }


def to_markdown(summary, issues, examples_per_rule=5):
    lines = [
        "# Data Quality Report", "",
        f"- **Source:** {summary['source']}",
        f"- **Rules:** {summary['rules']}",
        f"- **Status:** {summary['status']}" + (
            f" (up to {summary['max_error_rate']}% of rows may have errors)"
            if summary.get("max_error_rate") is not None else ""),
        f"- **Rows checked:** {summary['total_rows']}",
        f"- **Rows with errors:** {summary['rows_with_errors']} "
        f"(row pass rate {summary['row_pass_rate']}%)",
        f"- **Errors:** {summary['errors']}, **Warnings:** {summary['warnings']}", "",
    ]
    if not issues:
        lines.append("No issues found.")
        return "\n".join(lines) + "\n"

    lines += ["## Issues by rule", "", "| Rule | Count |", "| --- | --- |"]
    for rule, count in sorted(summary["by_rule"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {rule} | {count} |")
    lines += ["", "## Issues by column", "", "| Column | Count |", "| --- | --- |"]
    for col, count in sorted(summary["by_column"].items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {col} | {count} |")

    lines += ["", "## Examples", ""]
    by_rule = {}
    for issue in issues:
        by_rule.setdefault(issue["rule"], []).append(issue)
    for rule in sorted(by_rule):
        lines.append(f"### {rule}")
        for issue in by_rule[rule][:examples_per_rule]:
            where = f"line {issue['row']}" if issue["row"] else "file"
            col = f", {issue['column']}" if issue["column"] else ""
            lines.append(f"- {where}{col}: {issue['message']} ({issue['severity']})")
        extra = len(by_rule[rule]) - examples_per_rule
        if extra > 0:
            lines.append(f"- ...and {extra} more")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_junit(summary, issues, columns):
    """JUnit XML, the test report format that GitHub Actions, Jenkins, and Azure DevOps display.

    Each rules column is one test case, plus one for file-wide checks. Errors make it fail;
    warnings are listed in its output without failing it.
    """
    names = list(columns) + ["(dataset)"]
    by_column = {name: [] for name in names}
    for issue in issues:
        by_column.setdefault(issue["column"] or "(dataset)", []).append(issue)

    suite_name = f"qualitygate: {summary['source'] or summary['rules']}"
    suite = ET.Element("testsuite", name=suite_name, tests=str(len(by_column)))
    failures = 0
    for name, found in by_column.items():
        case = ET.SubElement(suite, "testcase", classname=suite_name, name=name)
        errors = [i for i in found if i["severity"] == "error"]
        if errors:
            failures += 1
            failure = ET.SubElement(case, "failure", message=f"{len(errors)} data quality error(s)", type="error")
            failure.text = "\n".join(_where(i) + i["message"] for i in errors)
        warnings = [i for i in found if i["severity"] == "warning"]
        if warnings:
            ET.SubElement(case, "system-out").text = "\n".join("warning: " + _where(i) + i["message"]
                                                                 for i in warnings)
    suite.set("failures", str(failures))
    ET.indent(suite)
    return ET.tostring(suite, encoding="unicode", xml_declaration=True) + "\n"


def _where(issue):
    return f"line {issue['row']}: " if issue["row"] else "file: "
