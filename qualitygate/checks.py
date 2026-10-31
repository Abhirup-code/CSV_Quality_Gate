"""Core checks. Row numbers are CSV line numbers (header is line 1)."""
import csv
import datetime as dt
import math
import operator
import re

OPERATORS = {"<": operator.lt, "<=": operator.le, "==": operator.eq,
             "!=": operator.ne, ">": operator.gt, ">=": operator.ge}


def read_csv(path, delimiter=","):
    """Return (header, rows) where rows is a list of (line_number, cells)."""
    # utf-8-sig drops the invisible byte-order mark Excel puts at the start of "CSV UTF-8" files,
    # which would otherwise become part of the first column's name.
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=delimiter)
        header = next(reader, [])
        rows = [(n, cells) for n, cells in enumerate(reader, start=2) if cells]
    return [h.strip() for h in header], rows


def parse_value(text, col_type, fmt=None):
    """Convert text to its type, or raise ValueError."""
    if col_type == "int":
        return int(text)
    if col_type == "float":
        value = float(text)
        if math.isnan(value) or math.isinf(value):
            raise ValueError("not a finite number")
        return value
    if col_type == "date":
        return dt.datetime.strptime(text, fmt or "%Y-%m-%d").date()
    return text


def _bound(spec, key, col_type):
    """The min or max to compare with, as a number or a date. "today" means the date of the run."""
    if key not in spec:
        return None
    if col_type != "date":
        return spec[key]
    if spec[key] == "today":
        return dt.date.today()
    return parse_value(str(spec[key]), "date", spec.get("format"))


def check_cell(raw, spec):
    """Return a list of (rule, message) problems for one cell."""
    value = raw.strip()
    if value == "":
        return [("required", "value is missing")] if spec.get("required") else []

    col_type = spec.get("type", "string")
    try:
        parsed = parse_value(value, col_type, spec.get("format"))
    except ValueError:
        return [("type", f"'{value}' is not a valid {col_type}")]

    problems = []
    if col_type in {"int", "float", "date"}:
        low, high = _bound(spec, "min", col_type), _bound(spec, "max", col_type)
        if low is not None and parsed < low:
            problems.append(("min", f"{value} is {'before' if col_type == 'date' else 'below'} "
                                    f"the minimum of {spec['min']}"))
        if high is not None and parsed > high:
            problems.append(("max", f"{value} is {'after' if col_type == 'date' else 'above'} "
                                    f"the maximum of {spec['max']}"))
    if "allowed" in spec and value not in [str(a) for a in spec["allowed"]]:
        problems.append(("allowed", f"'{value}' is not one of {spec['allowed']}"))
    if "pattern" in spec and not re.fullmatch(spec["pattern"], value):
        problems.append(("pattern", f"'{value}' does not match the required pattern"))
    if "max_length" in spec and len(value) > spec["max_length"]:
        problems.append(("max_length", f"length {len(value)} exceeds {spec['max_length']}"))
    return problems


def _issue(row, column, rule, value, message, severity):
    return {"row": row, "column": column, "rule": rule, "value": value,
            "message": message, "severity": severity}


def run_checks(header, rows, rules):
    """Run every rule and return a list of issue dicts."""
    issues = []
    columns = rules["columns"]
    dataset = rules.get("dataset", {})

    index = {name: i for i, name in enumerate(header)}
    for name in columns:
        if name not in index:
            issues.append(_issue(None, name, "missing_column", None,
                                 f"column '{name}' is not in the file", "error"))

    if "min_rows" in dataset and len(rows) < dataset["min_rows"]:
        issues.append(_issue(None, None, "min_rows", len(rows),
                             f"file has {len(rows)} rows, expected at least {dataset['min_rows']}",
                             "error"))

    seen_unique = {name: {} for name, s in columns.items() if s.get("unique")}
    seen_rows = {}

    for line, cells in rows:
        if len(cells) != len(header):
            issues.append(_issue(line, None, "column_count", len(cells),
                                 f"row has {len(cells)} fields, expected {len(header)}", "error"))
            continue

        for name, spec in columns.items():
            if name not in index:
                continue
            raw = cells[index[name]]
            severity = spec.get("severity", "error")
            for rule, message in check_cell(raw, spec):
                issues.append(_issue(line, name, rule, raw.strip(), message, severity))
            value = raw.strip()
            if name in seen_unique and value:
                first = seen_unique[name].get(value)
                if first is None:
                    seen_unique[name][value] = line
                else:
                    issues.append(_issue(line, name, "unique", value,
                                         f"'{value}' already appears on line {first}", severity))

        for item in dataset.get("compare", []):
            problem = compare_cells(cells, index, columns, item)
            if problem:
                issues.append(_issue(line, item["left"], "compare", cells[index[item["left"]]].strip(),
                                     problem, item.get("severity", "error")))

        if dataset.get("no_duplicate_rows"):
            key = tuple(c.strip() for c in cells)
            first = seen_rows.get(key)
            if first is None:
                seen_rows[key] = line
            else:
                issues.append(_issue(line, None, "duplicate_row", None,
                                     f"row is identical to line {first}", "error"))
    return issues


def compare_cells(cells, index, columns, item):
    """A message if the row breaks a comparison like ship_date >= order_date, else None.

    A blank or unreadable value is skipped here: the column's own rules report it.
    """
    left, right = item["left"], item["right"]
    if left not in index or right not in index:
        return None
    raw_left, raw_right = cells[index[left]].strip(), cells[index[right]].strip()
    if not raw_left or not raw_right:
        return None
    try:
        a = parse_value(raw_left, columns[left].get("type", "string"), columns[left].get("format"))
        b = parse_value(raw_right, columns[right].get("type", "string"), columns[right].get("format"))
    except ValueError:
        return None
    if OPERATORS[item["op"]](a, b):
        return None
    return f"{left} {raw_left} is not {item['op']} {right} {raw_right}"
