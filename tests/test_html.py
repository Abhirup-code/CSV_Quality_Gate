import json
from pathlib import Path

from qualitygate.cli import main
from qualitygate.report import summarize, to_html

EX = Path(__file__).resolve().parent.parent / "examples"


def test_dirty_sample_html_report(tmp_path):
    main([str(EX / "orders_dirty.csv"), "--rules", str(EX / "orders_rules.json"), "--out", str(tmp_path)])
    page = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>") and page.endswith("</html>\n")
    assert "<title>Data quality: orders_dirty.csv</title>" in page
    assert '<p class="status FAIL">FAIL</p>' in page
    assert "<b>202</b>" in page and "<b>95.0%</b>" in page
    assert "&#x27;shiped&#x27; is not one of" in page
    assert "<script" not in page and "http" not in page  # no scripts or outside files


def test_clean_report_says_no_issues():
    page = to_html(summarize([], 3, source="a.csv"), [])
    assert '<p class="status PASS">PASS</p>' in page and "No issues found." in page


def test_every_value_is_escaped():
    issue = {"row": 2, "column": "<img src=x>", "rule": "<b>", "value": "x",
             "message": "<script>alert(1)</script>", "severity": "error"}
    page = to_html(summarize([issue], 1, source="<a>.csv", rules_name="r&d"), [issue])
    assert "<script>alert" not in page and "<img" not in page
    assert "<td>&lt;b&gt;</td>" in page and "<td>&lt;img src=x&gt;</td>" in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page and "Rules: r&amp;d" in page


def test_long_runs_show_a_sample_and_point_to_json():
    issues = [{"row": n, "column": "a", "rule": "x", "value": "", "message": "bad", "severity": "error"}
              for n in range(2, 32)]
    page = to_html(summarize(issues, 30), issues, examples_per_rule=25)
    assert page.count("<td>bad</td>") == 25 and "5 more issues are in report.json." in page


def test_tolerance_is_shown(tmp_path):
    main([str(EX / "orders_dirty.csv"), "--rules", str(EX / "orders_rules.json"), "--out", str(tmp_path),
          "--max-error-rate", "5"])
    assert "PASS (up to 5.0% of rows may have errors)" in (tmp_path / "report.html").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "report.json").read_text())["summary"]["status"] == "PASS"
