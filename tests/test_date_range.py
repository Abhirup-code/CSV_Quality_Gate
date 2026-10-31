import datetime as dt

import pytest

from qualitygate.checks import check_cell
from qualitygate.rules import RulesError, validate_rules


def spec(**extra):
    return validate_rules({"columns": {"d": {"type": "date", **extra}}})["columns"]["d"]


def test_dates_before_the_minimum_or_after_the_maximum_are_flagged():
    s = spec(min="2026-01-01", max="2026-06-30")
    assert check_cell("2026-03-15", s) == []
    assert check_cell("2025-12-31", s) == [("min", "2025-12-31 is before the minimum of 2026-01-01")]
    assert check_cell("2026-07-01", s) == [("max", "2026-07-01 is after the maximum of 2026-06-30")]


def test_today_catches_dates_in_the_future():
    s = spec(max="today")
    today = dt.date.today()
    assert check_cell(today.isoformat(), s) == []
    tomorrow = (today + dt.timedelta(days=1)).isoformat()
    assert check_cell(tomorrow, s) == [("max", f"{tomorrow} is after the maximum of today")]


def test_bounds_use_the_column_format():
    s = spec(format="%m/%d/%Y", min="01/15/2026")
    assert check_cell("01/14/2026", s)[0][0] == "min"
    assert check_cell("02/01/2026", s) == []


def test_numbers_still_compare_as_before():
    s = validate_rules({"columns": {"n": {"type": "float", "min": 0, "max": 10}}})["columns"]["n"]
    assert check_cell("-1", s) == [("min", "-1 is below the minimum of 0")]
    assert check_cell("11", s) == [("max", "11 is above the maximum of 10")]


@pytest.mark.parametrize(("column", "message"), [
    ({"type": "date", "min": "next week"}, "must be a date in the column's format"),
    ({"type": "date", "format": "%m/%d/%Y", "max": "2026-01-01"}, "must be a date in the column's format"),
    ({"type": "int", "min": "5"}, "min must be a number"),
    ({"type": "float", "max": True}, "max must be a number"),
    ({"type": "string", "min": 1}, "min/max need type int, float, or date"),
])
def test_rejects_bounds_that_do_not_fit_the_column(column, message):
    with pytest.raises(RulesError, match=message):
        validate_rules({"columns": {"c": column}})
