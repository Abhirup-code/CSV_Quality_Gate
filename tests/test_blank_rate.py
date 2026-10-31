import pytest

from qualitygate.checks import run_checks
from qualitygate.report import summarize
from qualitygate.rules import RulesError, validate_rules


def rows(*values):
    return [(n, [v]) for n, v in enumerate(values, start=2)]


def check(limit, *values, **extra):
    rules = validate_rules({"columns": {"phone": {"max_blank_rate": limit, **extra}}})
    return run_checks(["phone"], rows(*values), rules)


def test_within_the_limit_passes():
    assert check(25, "1", "2", "", "4") == []  # exactly 25%


def test_over_the_limit_is_one_file_wide_issue():
    issues = check(20, "1", "", "", "4")
    assert issues == [{"row": None, "column": "phone", "rule": "max_blank_rate", "value": 50.0,
                       "message": "50.0% of values are blank (2 of 4), more than the allowed 20%",
                       "severity": "error"}]
    assert summarize(issues, 4, max_error_rate=100)["status"] == "FAIL"  # tolerance never hides it


def test_can_be_a_warning_and_spaces_count_as_blank():
    issues = check(0, "1", "  ", severity="warning")
    assert issues[0]["severity"] == "warning" and issues[0]["value"] == 50.0


def test_rows_with_the_wrong_number_of_fields_are_not_counted():
    rules = validate_rules({"columns": {"a": {"max_blank_rate": 0}}})
    issues = run_checks(["a", "b"], [(2, ["x", "y"]), (3, ["", "y", "extra"])], rules)
    assert [i["rule"] for i in issues] == ["column_count"]


def test_an_empty_file_or_missing_column_does_not_divide_by_zero():
    assert check(0) == []
    rules = validate_rules({"columns": {"a": {"max_blank_rate": 0}}})
    assert [i["rule"] for i in run_checks(["b"], [(2, ["x"])], rules)] == ["missing_column"]


@pytest.mark.parametrize("bad", [-1, 101, "5", True])
def test_rejects_a_bad_percentage(bad):
    with pytest.raises(RulesError, match="max_blank_rate must be a percentage"):
        validate_rules({"columns": {"a": {"max_blank_rate": bad}}})
