"""Summaries and report formats."""
from collections import Counter


def summarize(issues, total_rows, source="", rules_name=""):
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    bad_rows = {i["row"] for i in errors if i["row"] is not None}
    clean = total_rows - len(bad_rows)
    return {
        "source": source,
        "rules": rules_name,
        "status": "FAIL" if errors else "PASS",
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
        f"- **Status:** {summary['status']}",
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
