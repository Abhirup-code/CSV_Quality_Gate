import csv
from pathlib import Path

from qualitygate.checks import read_csv, run_checks
from qualitygate.cli import main
from qualitygate.quarantine import split_rows
from qualitygate.rules import load_rules

EX = Path(__file__).resolve().parent.parent / "examples"


def issue(row, column, message, severity="error"):
    return {"row": row, "column": column, "rule": "x", "value": None, "message": message, "severity": severity}


def test_rows_with_errors_fail_with_every_reason_and_warnings_pass():
    rows = [(2, ["1"]), (3, ["2"]), (4, ["3"])]
    issues = [issue(3, "id", "too small"), issue(3, None, "row is identical to line 2"),
              issue(4, "id", "odd", severity="warning"), issue(None, None, "file is short")]
    passed, failed = split_rows(rows, issues)
    assert passed == [["1"], ["3"]]
    assert failed == [(3, ["2"], "id: too small; row is identical to line 2")]


def test_quarantine_files_for_the_dirty_sample(tmp_path, capsys):
    q = tmp_path / "q"
    code = main([str(EX / "orders_dirty.csv"), "--rules", str(EX / "orders_rules.json"),
                 "--out", str(tmp_path / "r"), "--quarantine", str(q)])
    assert code == 1
    assert "Quarantine: 192 rows in passed.csv, 10 rows in failed.csv" in capsys.readouterr().out

    with open(q / "passed.csv", newline="", encoding="utf-8") as f:
        passed = list(csv.reader(f))
    with open(q / "failed.csv", newline="", encoding="utf-8") as f:
        failed = list(csv.reader(f))
    header, rows = read_csv(EX / "orders_dirty.csv")
    assert passed[0] == header and len(passed) == 1 + 192
    assert failed[0] == ["_line", "_errors", *header] and len(failed) == 1 + 10
    assert any("status: 'shiped' is not one of" in r[1] for r in failed[1:])

    # The rows that passed really do pass, apart from the dataset-wide checks.
    q_header, q_rows = read_csv(q / "passed.csv")
    leftover = run_checks(q_header, q_rows, load_rules(EX / "orders_rules.json"))
    assert [i for i in leftover if i["severity"] == "error"] == []


def test_without_the_flag_no_quarantine_is_written(tmp_path):
    main([str(EX / "orders_clean.csv"), "--rules", str(EX / "orders_rules.json"), "--out", str(tmp_path)])
    assert not (tmp_path / "passed.csv").exists()
