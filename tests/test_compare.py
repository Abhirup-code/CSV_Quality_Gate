import re

import pytest

from qualitygate.checks import run_checks
from qualitygate.rules import RulesError, validate_rules


def rules(*comparisons, **columns):
    cols = columns or {"order_date": {"type": "date"}, "ship_date": {"type": "date"},
                       "price": {"type": "float"}, "cost": {"type": "int"}, "name": {}}
    return {"columns": cols, "dataset": {"compare": list(comparisons)}}


HEADER = ["order_date", "ship_date", "price", "cost", "name"]


def check(rule_set, *rows):
    return run_checks(HEADER, [(n, r) for n, r in enumerate(rows, start=2)], validate_rules(rule_set))


def test_flags_a_row_that_breaks_the_comparison():
    rule_set = rules({"left": "ship_date", "op": ">=", "right": "order_date"})
    issues = check(rule_set, ["2026-01-05", "2026-01-07", "1", "1", "a"],
                   ["2026-01-05", "2026-01-02", "1", "1", "b"])
    assert issues == [{"row": 3, "column": "ship_date", "rule": "compare", "value": "2026-01-02",
                       "message": "ship_date 2026-01-02 is not >= order_date 2026-01-05",
                       "severity": "error"}]


def test_compares_numbers_as_numbers_not_text():
    rule_set = rules({"left": "price", "op": ">", "right": "cost", "severity": "warning"})
    assert check(rule_set, ["2026-01-01", "2026-01-01", "10.5", "9", "a"]) == []  # "10.5" < "9" as text
    issues = check(rule_set, ["2026-01-01", "2026-01-01", "8", "9", "a"])
    assert issues[0]["severity"] == "warning"


@pytest.mark.parametrize(("op", "left", "right", "ok"), [
    ("<", "1", "2", True), ("<=", "2", "2", True), ("==", "2", "2", True),
    ("!=", "2", "2", False), (">", "1", "2", False), (">=", "1", "2", False)])
def test_every_operator(op, left, right, ok):
    rule_set = {"columns": {"a": {"type": "int"}, "b": {"type": "int"}},
                "dataset": {"compare": [{"left": "a", "op": op, "right": "b"}]}}
    issues = run_checks(["a", "b"], [(2, [left, right])], validate_rules(rule_set))
    assert (issues == []) is ok


def test_skips_blank_and_unreadable_values_that_other_rules_report():
    rule_set = rules({"left": "ship_date", "op": ">=", "right": "order_date"})
    issues = check(rule_set, ["2026-01-05", "", "1", "1", "a"], ["2026-01-05", "soon", "1", "1", "a"])
    assert [i["rule"] for i in issues] == ["type"]  # the date column reports "soon"; compare adds nothing


def test_skips_when_a_column_is_missing_from_the_file():
    rule_set = validate_rules(rules({"left": "ship_date", "op": ">=", "right": "order_date"}))
    issues = run_checks(["order_date"], [(2, ["2026-01-01"])], rule_set)
    assert {i["rule"] for i in issues} == {"missing_column"}


@pytest.mark.parametrize(("comparisons", "message"), [
    ("not a list", "'compare' must be a list"),
    (["x"], "compare #1: must be an object"),
    ([{"left": "price", "op": ">", "right": "cost", "when": 1}], "unknown key(s) ['when']"),
    ([{"left": "nope", "op": ">", "right": "cost"}], "'left' must name a column"),
    ([{"left": "price", "op": ">", "right": "nope"}], "'right' must name a column"),
    ([{"left": "price", "op": "=>", "right": "cost"}], "'op' must be one of"),
    ([{"left": "price", "op": ">", "right": "cost", "severity": "fatal"}], "severity must be"),
    ([{"left": "price", "op": ">", "right": "order_date"}], "have different types"),
    ([{"left": "name", "op": ">", "right": "order_date"}], "have different types"),
])
def test_rejects_bad_comparisons(comparisons, message):
    rule_set = rules()
    rule_set["dataset"]["compare"] = comparisons
    with pytest.raises(RulesError, match=re.escape(message)):
        validate_rules(rule_set)
