import json
from pathlib import Path

import pytest

from qualitygate.cli import main
from qualitygate.report import summarize

EX = Path(__file__).resolve().parent.parent / "examples"
RULES = str(EX / "orders_rules.json")


def row_error(row):
    return {"row": row, "column": "a", "rule": "x", "value": None, "message": "bad", "severity": "error"}


def test_without_a_tolerance_any_error_fails():
    s = summarize([row_error(2)], 100)
    assert s["status"] == "FAIL" and s["row_error_rate"] == 1.0 and s["max_error_rate"] is None


def test_errors_within_the_tolerance_pass_and_above_it_fail():
    issues = [row_error(n) for n in range(2, 7)]  # 5 bad rows out of 100
    assert summarize(issues, 100, max_error_rate=5)["status"] == "PASS"
    assert summarize(issues, 100, max_error_rate=4.9)["status"] == "FAIL"


def test_several_errors_on_one_row_count_once():
    assert summarize([row_error(2), row_error(2)], 50, max_error_rate=2)["status"] == "PASS"


def test_file_wide_errors_always_fail():
    missing_column = {**row_error(None), "rule": "missing_column"}
    assert summarize([missing_column], 100, max_error_rate=100)["status"] == "FAIL"


def test_dirty_sample_passes_at_5_percent_and_fails_at_4(tmp_path, capsys):
    # 10 of its 202 rows have errors (4.95%). Its duplicate and short rows are row problems, so they count too.
    base = [str(EX / "orders_dirty.csv"), "--rules", RULES, "--out", str(tmp_path)]
    assert main([*base, "--max-error-rate", "5"]) == 0
    summary = json.loads((tmp_path / "report.json").read_text())["summary"]
    assert summary["status"] == "PASS" and summary["errors"] == 11 and summary["row_error_rate"] == 5.0
    assert "(up to 5.0% of rows may have errors)" in (tmp_path / "report.md").read_text()
    assert main([*base, "--max-error-rate", "4"]) == 1


def test_warnings_can_still_fail_the_run(tmp_path):
    base = [str(EX / "orders_dirty.csv"), "--rules", RULES, "--out", str(tmp_path)]
    assert main([*base, "--max-error-rate", "10", "--fail-on-warning"]) == 1


@pytest.mark.parametrize("bad", ["-1", "101", "lots"])
def test_rejects_a_bad_percentage(tmp_path, bad, capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(EX / "orders_clean.csv"), "--rules", RULES, "--max-error-rate", bad])
    assert exc.value.code == 2
    assert "--max-error-rate" in capsys.readouterr().err
