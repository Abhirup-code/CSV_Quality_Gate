from qualitygate.checks import check_cell, parse_value, run_checks


def rules_of(**spec):
    return {"columns": {"c": spec}}


def rule_names(raw, **spec):
    return [r for r, _ in check_cell(raw, spec)]


def test_required_blank_and_whitespace():
    assert rule_names("", required=True) == ["required"]
    assert rule_names("   ", required=True) == ["required"]


def test_optional_blank_is_fine():
    assert rule_names("", type="int") == []


def test_int_type():
    assert rule_names("12", type="int") == []
    assert rule_names("12.5", type="int") == ["type"]
    assert rule_names("abc", type="int") == ["type"]


def test_float_rejects_nan_and_inf():
    assert rule_names("nan", type="float") == ["type"]
    assert rule_names("inf", type="float") == ["type"]


def test_min_and_max():
    assert rule_names("-1", type="float", min=0) == ["min"]
    assert rule_names("11", type="int", max=10) == ["max"]
    assert rule_names("5", type="int", min=0, max=10) == []


def test_date_default_and_custom_format():
    assert rule_names("2026-02-30", type="date") == ["type"]
    assert rule_names("2026-02-28", type="date") == []
    assert rule_names("28/02/2026", type="date", format="%d/%m/%Y") == []


def test_allowed_values():
    assert rule_names("red", allowed=["red", "blue"]) == []
    assert rule_names("green", allowed=["red", "blue"]) == ["allowed"]


def test_pattern_uses_full_match():
    assert rule_names("abc123", pattern="[a-z]+[0-9]+") == []
    assert rule_names("abc123!", pattern="[a-z]+[0-9]+") == ["pattern"]


def test_max_length():
    assert rule_names("abcdef", max_length=5) == ["max_length"]


def test_parse_value_string_passthrough():
    assert parse_value("hi", "string") == "hi"


def test_unique_flags_second_occurrence_only():
    rows = [(2, ["1"]), (3, ["2"]), (4, ["1"])]
    issues = run_checks(["c"], rows, rules_of(unique=True))
    assert [(i["row"], i["rule"]) for i in issues] == [(4, "unique")]


def test_missing_column_reported():
    issues = run_checks(["other"], [(2, ["x"])], rules_of(required=True))
    assert issues[0]["rule"] == "missing_column"


def test_wrong_field_count():
    issues = run_checks(["a", "b"], [(2, ["1"])], {"columns": {"a": {}}})
    assert issues[0]["rule"] == "column_count"


def test_duplicate_rows_and_min_rows():
    rules = {"columns": {"a": {}}, "dataset": {"no_duplicate_rows": True, "min_rows": 5}}
    issues = run_checks(["a"], [(2, ["x"]), (3, ["x"])], rules)
    assert sorted(i["rule"] for i in issues) == ["duplicate_row", "min_rows"]


def test_warning_severity_is_carried():
    issues = run_checks(["c"], [(2, ["z"])], rules_of(allowed=["a"], severity="warning"))
    assert issues[0]["severity"] == "warning"


def test_reads_a_csv_saved_by_excel_with_a_byte_order_mark(tmp_path):
    from qualitygate.checks import read_csv, run_checks
    path = tmp_path / "excel.csv"
    path.write_bytes(b"\xef\xbb\xbforder_id,amount\r\n1,2\r\n")
    header, rows = read_csv(path)
    assert header == ["order_id", "amount"] and rows == [(2, ["1", "2"])]
    assert run_checks(header, rows, {"columns": {"order_id": {"type": "int", "required": True}}}) == []
