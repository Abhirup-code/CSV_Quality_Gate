import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from qualitygate.cli import folder_names, main

EX = Path(__file__).resolve().parent.parent / "examples"
RULES = str(EX / "orders_rules.json")
CLEAN, DIRTY = str(EX / "orders_clean.csv"), str(EX / "orders_dirty.csv")


def test_each_file_gets_its_own_reports_and_one_failure_fails_the_run(tmp_path, capsys):
    code = main([CLEAN, DIRTY, "--rules", RULES, "--out", str(tmp_path / "r"), "--quarantine", str(tmp_path / "q")])
    assert code == 1
    out = capsys.readouterr().out
    assert "1 of 2 files passed." in out
    clean = json.loads((tmp_path / "r" / "orders_clean" / "report.json").read_text())["summary"]
    dirty = json.loads((tmp_path / "r" / "orders_dirty" / "report.json").read_text())["summary"]
    assert (clean["status"], dirty["status"]) == ("PASS", "FAIL")
    assert (tmp_path / "r" / "orders_dirty" / "report.html").exists()
    assert (tmp_path / "q" / "orders_dirty" / "failed.csv").exists()


def test_all_good_files_pass(tmp_path, capsys):
    other = tmp_path / "data" / "orders_clean.csv"
    other.parent.mkdir()
    shutil.copy(CLEAN, other)
    assert main([CLEAN, str(other), "--rules", RULES, "--out", str(tmp_path / "r")]) == 0
    assert "2 of 2 files passed." in capsys.readouterr().out
    assert (tmp_path / "r" / "orders_clean-2" / "report.json").exists()  # same name, own folder


def test_an_unreadable_file_is_reported_and_the_others_still_run(tmp_path, capsys):
    code = main([str(tmp_path / "missing.csv"), CLEAN, "--rules", RULES, "--out", str(tmp_path / "r")])
    assert code == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("error:") and "1 of 2 files passed." in captured.out
    assert (tmp_path / "r" / "orders_clean" / "report.json").exists()


def test_junit_has_one_suite_per_file(tmp_path):
    junit = tmp_path / "junit.xml"
    main([CLEAN, DIRTY, "--rules", RULES, "--out", str(tmp_path / "r"), "--junit", str(junit)])
    root = ET.fromstring(junit.read_text(encoding="utf-8").split("?>", 1)[1])
    assert root.tag == "testsuites" and root.get("tests") == "14" and root.get("failures") == "6"
    assert [s.get("name") for s in root] == ["qualitygate: orders_clean.csv", "qualitygate: orders_dirty.csv"]


def test_one_file_keeps_the_simple_layout(tmp_path):
    main([CLEAN, "--rules", RULES, "--out", str(tmp_path)])
    assert (tmp_path / "report.json").exists() and not (tmp_path / "orders_clean").exists()


def test_folder_names_are_unique():
    assert folder_names(["a/x.csv", "b/x.csv", "y.csv", "c/x.csv"]) == ["x", "x-2", "y", "x-3"]
    assert folder_names(["x.csv", "x-2.csv", "b/x.csv"]) == ["x", "x-2", "x-3"]
