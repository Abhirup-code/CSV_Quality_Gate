import json
from pathlib import Path

from qualitygate.cli import main

EX = Path(__file__).resolve().parent.parent / "examples"
RULES = str(EX / "orders_rules.json")


def run(csv_name, tmp_path, *extra):
    code = main([str(EX / csv_name), "--rules", RULES, "--out", str(tmp_path), *extra])
    return code, json.loads((tmp_path / "report.json").read_text())["summary"]


def test_clean_file_passes(tmp_path):
    code, summary = run("orders_clean.csv", tmp_path)
    assert code == 0 and summary["total_rows"] == 200 and summary["errors"] == 0


def test_dirty_file_fails_with_known_counts(tmp_path):
    code, summary = run("orders_dirty.csv", tmp_path)
    assert code == 1
    assert summary["total_rows"] == 202
    assert summary["errors"] == 11 and summary["warnings"] == 1
    assert summary["rows_with_errors"] == 10 and summary["row_pass_rate"] == 95.0
    assert summary["by_rule"]["unique"] == 2 and summary["by_rule"]["column_count"] == 1


def test_reports_are_written(tmp_path):
    run("orders_dirty.csv", tmp_path)
    assert (tmp_path / "report.json").exists()
    assert "# Data Quality Report" in (tmp_path / "report.md").read_text()


def test_missing_csv_is_usage_error(tmp_path, capsys):
    code = main([str(tmp_path / "nope.csv"), "--rules", RULES, "--out", str(tmp_path)])
    assert code == 2 and "error:" in capsys.readouterr().err


def test_bad_rules_is_usage_error(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    code = main([str(EX / "orders_clean.csv"), "--rules", str(bad), "--out", str(tmp_path)])
    assert code == 2


def test_fail_on_warning(tmp_path):
    csv_path = tmp_path / "w.csv"
    csv_path.write_text("order_id,customer_email,order_date,region,amount,status\n"
                        "1,a@b.co,2026-01-01,Mars,10,pending\n")
    args = [str(csv_path), "--rules", RULES, "--out", str(tmp_path / "o")]
    assert main(args) == 0
    assert main(args + ["--fail-on-warning"]) == 1


def test_infer_prints_rules_the_clean_file_passes(tmp_path, capsys):
    assert main(["infer", str(EX / "orders_clean.csv")]) == 0
    rules = json.loads(capsys.readouterr().out)
    assert rules["name"] == "orders_clean" and rules["columns"]["order_id"]["unique"] is True
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(rules))
    code = main([str(EX / "orders_clean.csv"), "--rules", str(rules_path), "--out", str(tmp_path / "r")])
    assert code == 0


def test_infer_writes_a_file_with_a_chosen_name(tmp_path, capsys):
    out = tmp_path / "orders.json"
    assert main(["infer", str(EX / "orders_clean.csv"), "--out", str(out), "--name", "orders"]) == 0
    assert json.loads(out.read_text())["name"] == "orders"
    assert "Review them before use" in capsys.readouterr().err


def test_infer_reports_a_missing_file(tmp_path, capsys):
    assert main(["infer", str(tmp_path / "nope.csv")]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_infer_creates_the_output_folder(tmp_path):
    out = tmp_path / "new" / "folder" / "rules.json"
    assert main(["infer", str(EX / "orders_clean.csv"), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["columns"]


def test_infer_reports_an_output_path_it_cannot_write(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert main(["infer", str(EX / "orders_clean.csv"), "--out", str(blocker / "rules.json")]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_version(capsys):
    import pytest
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0 and capsys.readouterr().out.strip() == "qualitygate 1.3.0"
