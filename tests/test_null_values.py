"""Placeholders that mean "no value": NULL, N/A, -, and the rest."""
import pytest

from qualitygate.checks import check_cell, is_blank, null_set, run_checks
from qualitygate.rules import RulesError, validate_rules

HEADER = ["order_id", "region", "ship_date", "order_date"]


def rules(**dataset):
    return {
        "columns": {
            "order_id": {"type": "int", "required": True, "unique": True},
            "region": {"type": "string", "allowed": ["South", "West"]},
            "ship_date": {"type": "date", "required": True},
            "order_date": {"type": "date"},
        },
        "dataset": dataset,
    }


def row(line, *cells):
    return (line, list(cells))


@pytest.mark.parametrize(
    "value, blank",
    [("", True), ("   ", True), ("NULL", True), ("null", True), (" N/A ", True), ("-", True),
     ("0", False), ("South", False), ("not available", False)],
)
def test_a_placeholder_counts_as_no_value(value, blank):
    assert is_blank(value, null_set({"null_values": ["NULL", "N/A", "-"]})) is blank


def test_without_a_list_only_an_empty_cell_is_blank():
    assert is_blank("", ()) and not is_blank("NULL", ())


def test_a_column_overrides_the_dataset_list():
    dataset = {"null_values": ["NULL"]}
    assert null_set({"null_values": ["-"]}, dataset) == {"-"}
    assert null_set({}, dataset) == {"null"}


def test_a_required_cell_says_which_placeholder_it_found():
    spec = {"type": "int", "required": True}
    assert check_cell("N/A", spec, {"n/a"}) == [("required", "value is missing ('N/A' stands for no value)")]
    assert check_cell("", spec) == [("required", "value is missing")]


def test_a_placeholder_is_not_a_type_error():
    """Before this, "NULL" in a date column was reported as a bad date, which hid the real problem."""
    spec = {"type": "date"}
    assert check_cell("NULL", spec) == [("type", "'NULL' is not a valid date")]
    assert check_cell("NULL", spec, {"null"}) == []


@pytest.mark.parametrize("placeholder", ["NULL", "N/A", "-"])
def test_a_placeholder_in_an_optional_column_passes_every_other_rule(placeholder):
    issues = run_checks(
        HEADER,
        [row(2, "1", placeholder, "2026-01-02", "2026-01-01")],
        rules(null_values=["NULL", "N/A", "-"]),
    )
    assert issues == []


def test_the_same_placeholder_twice_is_not_a_duplicate_value():
    """Two rows with no order id are two missing ids, not a uniqueness problem."""
    rows = [row(2, "NULL", "South", "2026-01-02", "2026-01-01"),
            row(3, "NULL", "West", "2026-01-03", "2026-01-01")]
    issues = run_checks(HEADER, rows, rules(null_values=["NULL"]))
    assert [(i["row"], i["rule"]) for i in issues] == [(2, "required"), (3, "required")]


def test_a_placeholder_skips_the_comparison_like_a_blank():
    spec = rules(null_values=["N/A"], compare=[{"left": "ship_date", "op": ">=", "right": "order_date"}])
    spec["columns"]["ship_date"]["required"] = False
    rows = [row(2, "1", "South", "N/A", "2026-01-05")]
    assert run_checks(HEADER, rows, spec) == []
    # A real date that breaks the comparison is still reported.
    rows = [row(2, "1", "South", "2026-01-01", "2026-01-05")]
    assert [i["rule"] for i in run_checks(HEADER, rows, spec)] == ["compare"]


def test_placeholders_count_towards_the_blank_rate():
    spec = rules(null_values=["N/A"])
    spec["columns"]["region"] = {"type": "string", "max_blank_rate": 25}
    rows = [row(2, "1", "N/A", "2026-01-02", "2026-01-01"),
            row(3, "2", "South", "2026-01-02", "2026-01-01")]
    issue = run_checks(HEADER, rows, spec)[0]
    assert issue["rule"] == "max_blank_rate" and issue["value"] == 50.0


@pytest.mark.parametrize("bad", [["NULL", ""], ["NULL", 7], "NULL", {"a": 1}, [None]])
def test_a_bad_null_values_list_is_refused(bad):
    with pytest.raises(RulesError, match="null_values"):
        validate_rules({"columns": {"a": {"null_values": bad}}})
    with pytest.raises(RulesError, match="null_values"):
        validate_rules({"columns": {"a": {}}, "dataset": {"null_values": bad}})


def test_a_good_null_values_list_is_accepted():
    validate_rules({"columns": {"a": {"null_values": ["NULL"]}}, "dataset": {"null_values": ["N/A"]}})
