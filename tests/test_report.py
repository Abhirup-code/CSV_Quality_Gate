from qualitygate.report import summarize, to_markdown


def issue(row, rule="min", severity="error", column="amount"):
    return {"row": row, "column": column, "rule": rule, "value": "x",
            "message": "m", "severity": severity}


def test_clean_summary_passes():
    s = summarize([], 10)
    assert s["status"] == "PASS" and s["row_pass_rate"] == 100.0


def test_row_pass_rate_counts_each_bad_row_once():
    s = summarize([issue(2), issue(2, rule="max"), issue(3)], 10)
    assert s["rows_with_errors"] == 2 and s["row_pass_rate"] == 80.0


def test_warnings_do_not_fail():
    s = summarize([issue(2, severity="warning")], 10)
    assert s["status"] == "PASS" and s["warnings"] == 1 and s["errors"] == 0


def test_empty_file_summary():
    assert summarize([], 0)["row_pass_rate"] == 100.0


def test_markdown_contains_key_sections():
    issues = [issue(2), issue(3, rule="required", column="email")]
    md = to_markdown(summarize(issues, 5), issues)
    assert "## Issues by rule" in md and "### required" in md and "FAIL" in md


def test_markdown_truncates_examples():
    issues = [issue(n) for n in range(2, 12)]
    md = to_markdown(summarize(issues, 20), issues, examples_per_rule=3)
    assert "...and 7 more" in md


def test_markdown_for_clean_file():
    assert "No issues found." in to_markdown(summarize([], 3), [])
