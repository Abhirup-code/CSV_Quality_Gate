from pathlib import Path

from qualitygate.checks import read_csv, run_checks
from qualitygate.infer import infer_column, infer_rules
from qualitygate.rules import validate_rules

EX = Path(__file__).resolve().parent.parent / "examples"


def test_infers_types_in_order_int_float_date_string():
    assert infer_column(["1", "2"])["type"] == "int"
    assert infer_column(["1", "2.5"])["type"] == "float"
    assert infer_column(["2026-01-05", "2026-02-01"]) == {
        "type": "date", "format": "%Y-%m-%d", "required": True}
    assert infer_column(["1", "abc"])["type"] == "string"


def test_nan_and_infinity_are_not_numbers():
    assert infer_column(["1.5", "nan"])["type"] == "string"
    assert infer_column(["inf", "2"])["type"] == "string"


def test_required_only_when_no_value_is_blank():
    assert infer_column(["a", "b"])["required"] is True
    assert "required" not in infer_column(["a", " "])
    assert "required" not in infer_column([])


def test_unique_for_distinct_ids_and_text_but_not_amounts_or_dates():
    assert infer_column(["1", "2", "3"])["unique"] is True
    assert infer_column(["a@x.com", "b@x.com"])["unique"] is True
    assert "unique" not in infer_column(["1.5", "2.5"])
    assert "unique" not in infer_column(["2026-01-01", "2026-01-02"])
    assert "unique" not in infer_column(["7"])
    assert "unique" not in infer_column(["a", "a"])


def test_minimum_of_zero_only_when_nothing_is_negative():
    assert infer_column(["0", "5"])["min"] == 0
    assert "min" not in infer_column(["-1", "5"])
    assert "max" not in infer_column(["0", "5"])


def test_allowed_values_only_for_a_few_repeating_values():
    assert infer_column(["West", "South", "West", "South"])["allowed"] == ["South", "West"]
    assert "allowed" not in infer_column(["a", "b", "c"])  # nothing repeats
    many = [str(i) + "x" for i in range(11)] * 2
    assert "allowed" not in infer_column(many)


def test_rules_for_the_clean_sample_are_valid_and_the_sample_passes_them():
    header, rows = read_csv(EX / "orders_clean.csv")
    rules = validate_rules(infer_rules(header, rows, name="orders"))
    assert list(rules["columns"]) == header
    assert rules["columns"]["order_id"] == {"type": "int", "required": True, "unique": True, "min": 0}
    assert rules["columns"]["region"]["allowed"] == ["Midwest", "Northeast", "South", "West"]
    assert rules["dataset"] == {"min_rows": 1, "no_duplicate_rows": True}
    assert run_checks(header, rows, rules) == []


def test_inferred_rules_catch_most_planted_problems_in_the_dirty_sample():
    header, rows = read_csv(EX / "orders_clean.csv")
    rules = infer_rules(header, rows)
    header, dirty = read_csv(EX / "orders_dirty.csv")
    found = {i["rule"] for i in run_checks(header, dirty, rules)}
    assert {"unique", "type", "allowed", "column_count", "duplicate_row", "required", "min"} <= found


def test_skips_malformed_rows_and_handles_an_empty_file():
    rules = infer_rules(["a", "b"], [(2, ["1", "2"]), (3, ["oops"])])
    assert rules["columns"]["a"]["type"] == "int"
    empty = infer_rules(["a"], [])
    assert empty["columns"] == {"a": {"type": "string"}} and empty["dataset"] == {"no_duplicate_rows": True}
