import xml.etree.ElementTree as ET
from pathlib import Path

from qualitygate.cli import main
from qualitygate.report import summarize, to_junit

EX = Path(__file__).resolve().parent.parent / "examples"
RULES = str(EX / "orders_rules.json")


def cases(xml_text):
    suite = ET.fromstring(xml_text.split("?>", 1)[1])
    return suite, {c.get("name"): c for c in suite.iter("testcase")}


def test_dirty_sample_fails_the_right_columns(tmp_path):
    junit = tmp_path / "ci" / "junit.xml"
    assert main([str(EX / "orders_dirty.csv"), "--rules", RULES, "--out", str(tmp_path), "--junit", str(junit)]) == 1
    text = junit.read_text(encoding="utf-8")
    assert text.startswith("<?xml version='1.0' encoding='utf-8'?>")
    suite, by_name = cases(text)
    assert suite.get("name") == "qualitygate: orders_dirty.csv"
    assert suite.get("tests") == "7" and suite.get("failures") == "6"
    assert by_name["region"].find("failure") is None  # only a warning
    assert "warning: line 52: 'Mars'" in by_name["region"].find("system-out").text
    amount = by_name["amount"].find("failure")
    assert amount.get("message") == "3 data quality error(s)"
    assert "row has" not in amount.text  # file-wide and row-shape problems go to (dataset)
    assert by_name["(dataset)"].find("failure").text == (
        "line 202: row is identical to line 82\nline 203: row has 2 fields, expected 6")


def test_clean_sample_passes_every_case(tmp_path):
    junit = tmp_path / "junit.xml"
    assert main([str(EX / "orders_clean.csv"), "--rules", RULES, "--out", str(tmp_path), "--junit", str(junit)]) == 0
    suite, by_name = cases(junit.read_text(encoding="utf-8"))
    assert suite.get("failures") == "0" and len(by_name) == 7
    assert all(c.find("failure") is None for c in by_name.values())


def test_names_and_messages_with_markup_are_escaped():
    issues = [{"row": 2, "column": "<b>", "rule": "x", "value": "&", "message": "'<&>' is bad", "severity": "error"}]
    text = to_junit(summarize(issues, 1, source="a&b.csv"), issues, {"<b>": {}})
    suite, by_name = cases(text)
    assert suite.get("name") == "qualitygate: a&b.csv"
    assert by_name["<b>"].find("failure").text == "line 2: '<&>' is bad"
