"""Load and validate a JSON rules file."""
import json
import re

VALID_TYPES = {"string", "int", "float", "date"}
COLUMN_KEYS = {"type", "required", "unique", "min", "max", "allowed",
               "pattern", "format", "max_length", "severity"}
DATASET_KEYS = {"min_rows", "no_duplicate_rows"}
SEVERITIES = {"error", "warning"}


class RulesError(ValueError):
    """Raised when a rules file is malformed."""


def validate_rules(rules):
    if not isinstance(rules, dict):
        raise RulesError("rules file must contain a JSON object")
    columns = rules.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise RulesError("rules must define a non-empty 'columns' object")

    for name, spec in columns.items():
        if not isinstance(spec, dict):
            raise RulesError(f"column '{name}': rules must be an object")
        unknown = set(spec) - COLUMN_KEYS
        if unknown:
            raise RulesError(f"column '{name}': unknown rule(s) {sorted(unknown)}")
        col_type = spec.get("type", "string")
        if col_type not in VALID_TYPES:
            raise RulesError(f"column '{name}': type must be one of {sorted(VALID_TYPES)}")
        if spec.get("severity", "error") not in SEVERITIES:
            raise RulesError(f"column '{name}': severity must be 'error' or 'warning'")
        if ("min" in spec or "max" in spec) and col_type not in {"int", "float"}:
            raise RulesError(f"column '{name}': min/max need type int or float")
        if "pattern" in spec:
            try:
                re.compile(spec["pattern"])
            except re.error as exc:
                raise RulesError(f"column '{name}': bad pattern ({exc})") from exc

    unknown = set(rules.get("dataset", {})) - DATASET_KEYS
    if unknown:
        raise RulesError(f"dataset: unknown rule(s) {sorted(unknown)}")
    return rules


def load_rules(path):
    try:
        with open(path, encoding="utf-8") as f:
            rules = json.load(f)
    except json.JSONDecodeError as exc:
        raise RulesError(f"rules file is not valid JSON: {exc}") from exc
    return validate_rules(rules)
