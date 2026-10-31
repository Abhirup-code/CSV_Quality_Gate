import json
from pathlib import Path

import pytest

from qualitygate.cli import delimiter, main

EX = Path(__file__).resolve().parent.parent / "examples"
RULES = str(EX / "orders_rules.json")


def as_separated(tmp_path, sep):
    """The clean sample rewritten with another separator, the way European Excel saves it."""
    text = (EX / "orders_clean.csv").read_text(encoding="utf-8").replace(",", sep)
    path = tmp_path / "orders.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(("name", "sep"), [("semicolon", ";"), (";", ";"), ("tab", "\t"), ("\\t", "\t"), ("pipe", "|")])
def test_checks_files_with_other_separators(tmp_path, name, sep):
    path = as_separated(tmp_path, sep)
    assert main([path, "--rules", RULES, "--out", str(tmp_path / "r"), "--delimiter", name]) == 0


def test_the_wrong_separator_reports_missing_columns(tmp_path):
    path = as_separated(tmp_path, ";")
    assert main([path, "--rules", RULES, "--out", str(tmp_path / "r")]) == 1
    summary = json.loads((tmp_path / "r" / "report.json").read_text())["summary"]
    assert summary["by_rule"]["missing_column"] == 6


def test_infer_and_quarantine_use_the_same_separator(tmp_path, capsys):
    path = as_separated(tmp_path, ";")
    assert main(["infer", path, "--delimiter", "semicolon"]) == 0
    assert "order_id" in json.loads(capsys.readouterr().out)["columns"]
    main([path, "--rules", RULES, "--out", str(tmp_path / "r"), "--delimiter", ";",
          "--quarantine", str(tmp_path / "q")])
    assert (tmp_path / "q" / "passed.csv").read_text(encoding="utf-8").startswith("order_id;customer_email;")


@pytest.mark.parametrize("bad", ["", ";;", "\n", '"'])
def test_rejects_a_bad_separator(bad):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError):
        delimiter(bad)
