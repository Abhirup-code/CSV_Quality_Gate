"""Load and validate a JSON rules file."""
import datetime as dt
import json
import re

VALID_TYPES = {"string", "int", "float", "date"}
COLUMN_KEYS = {"type", "required", "unique", "min", "max", "allowed",
               "pattern", "format", "max_length", "severity", "max_blank_rate"}
DATASET_KEYS = {"min_rows", "no_duplicate_rows", "compare"}
COMPARE_OPS = {"<", "<=", "==", "!=", ">", ">="}
COMPARE_KEYS = {"left", "op", "right", "severity"}
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
        if "max_blank_rate" in spec:
            rate = spec["max_blank_rate"]
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not 0 <= rate <= 100:
                raise RulesError(f"column '{name}': max_blank_rate must be a percentage from 0 to 100")
        for bound in ("min", "max"):
            if bound in spec:
                _check_bound(name, bound, spec[bound], col_type, spec.get("format"))
        if "pattern" in spec:
            try:
                re.compile(spec["pattern"])
            except re.error as exc:
                raise RulesError(f"column '{name}': bad pattern ({exc})") from exc

    unknown = set(rules.get("dataset", {})) - DATASET_KEYS
    if unknown:
        raise RulesError(f"dataset: unknown rule(s) {sorted(unknown)}")
    validate_compare(rules.get("dataset", {}).get("compare", []), columns)
    return rules


def _check_bound(name, bound, value, col_type, fmt):
    """min/max must be a number for number columns, or a date (or "today") for date columns."""
    where = f"column '{name}': {bound}"
    if col_type in {"int", "float"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RulesError(f"{where} must be a number")
    elif col_type == "date":
        if value == "today":
            return
        try:
            dt.datetime.strptime(str(value), fmt or "%Y-%m-%d")
        except ValueError:
            raise RulesError(f"{where} must be a date in the column's format, or \"today\"") from None
    else:
        raise RulesError(f"column '{name}': min/max need type int, float, or date")


def _kind(spec):
    col_type = spec.get("type", "string")
    return "number" if col_type in {"int", "float"} else col_type


def validate_compare(comparisons, columns):
    """Each comparison names two columns of the same kind and one of the six operators."""
    if not isinstance(comparisons, list):
        raise RulesError("dataset: 'compare' must be a list")
    for n, item in enumerate(comparisons, start=1):
        where = f"compare #{n}"
        if not isinstance(item, dict):
            raise RulesError(f"{where}: must be an object")
        unknown = set(item) - COMPARE_KEYS
        if unknown:
            raise RulesError(f"{where}: unknown key(s) {sorted(unknown)}")
        for side in ("left", "right"):
            if item.get(side) not in columns:
                raise RulesError(f"{where}: '{side}' must name a column in the rules")
        if item.get("op") not in COMPARE_OPS:
            raise RulesError(f"{where}: 'op' must be one of {sorted(COMPARE_OPS)}")
        if item.get("severity", "error") not in SEVERITIES:
            raise RulesError(f"{where}: severity must be 'error' or 'warning'")
        left, right = columns[item["left"]], columns[item["right"]]
        if _kind(left) != _kind(right):
            raise RulesError(f"{where}: '{item['left']}' and '{item['right']}' have different types")


def load_rules(path):
    try:
        with open(path, encoding="utf-8") as f:
            rules = json.load(f)
    except json.JSONDecodeError as exc:
        raise RulesError(f"rules file is not valid JSON: {exc}") from exc
    return validate_rules(rules)
