import json

import pytest

from qualitygate.rules import RulesError, load_rules, validate_rules


def test_valid_rules_load(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"columns": {"a": {"type": "int", "min": 0}}}))
    assert load_rules(p)["columns"]["a"]["type"] == "int"


def test_missing_columns_rejected():
    with pytest.raises(RulesError):
        validate_rules({"name": "x"})


def test_unknown_rule_rejected():
    with pytest.raises(RulesError, match="unknown rule"):
        validate_rules({"columns": {"a": {"minimum": 1}}})


def test_bad_type_rejected():
    with pytest.raises(RulesError, match="type"):
        validate_rules({"columns": {"a": {"type": "banana"}}})


def test_min_needs_numeric_type():
    with pytest.raises(RulesError, match="min/max"):
        validate_rules({"columns": {"a": {"type": "string", "min": 1}}})


def test_bad_regex_rejected():
    with pytest.raises(RulesError, match="pattern"):
        validate_rules({"columns": {"a": {"pattern": "("}}})


def test_bad_severity_rejected():
    with pytest.raises(RulesError, match="severity"):
        validate_rules({"columns": {"a": {"severity": "fatal"}}})


def test_unknown_dataset_rule_rejected():
    with pytest.raises(RulesError, match="dataset"):
        validate_rules({"columns": {"a": {}}, "dataset": {"max_rows": 5}})


def test_invalid_json_file(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(RulesError, match="not valid JSON"):
        load_rules(p)
