"""Draft a rules file from a CSV that is known to be good.

The draft is a starting point to review, not a final answer. It is deliberately loose where a
guess could be wrong: numbers only get "min": 0 when no value is negative (no maximum is
guessed), and a column only gets an "allowed" list when it has a few values that repeat.
"""
from .checks import parse_value

DATE_FORMAT = "%Y-%m-%d"
MAX_ALLOWED_VALUES = 10


def _all_parse(values, col_type, fmt=None):
    try:
        return [parse_value(v, col_type, fmt) for v in values]
    except ValueError:
        return None


def infer_column(values):
    """Rules for one column, from its raw cell values."""
    present = [v.strip() for v in values if v.strip()]
    spec = {"type": "string"}
    parsed = None
    if present:
        for col_type, fmt in (("int", None), ("float", None), ("date", DATE_FORMAT)):
            parsed = _all_parse(present, col_type, fmt)
            if parsed is not None:
                spec["type"] = col_type
                if fmt:
                    spec["format"] = fmt
                break

    if values and len(present) == len(values):
        spec["required"] = True
    distinct = set(present)
    if len(present) >= 2 and len(distinct) == len(present) and spec["type"] in {"int", "string"}:
        spec["unique"] = True
    if spec["type"] in {"int", "float"} and parsed and min(parsed) >= 0:
        spec["min"] = 0
    if spec["type"] == "string" and 2 <= len(distinct) <= MAX_ALLOWED_VALUES and len(present) >= 2 * len(distinct):
        spec["allowed"] = sorted(distinct)
    return spec


def infer_rules(header, rows, name="inferred"):
    """A rules object that the given file passes, built only from well-formed rows."""
    good = [cells for _, cells in rows if len(cells) == len(header)]
    index = {column: i for i, column in enumerate(header)}  # a repeated header name uses its last column
    columns = {column: infer_column([cells[i] for cells in good]) for column, i in index.items()}

    dataset = {}
    if good:
        dataset["min_rows"] = 1
    keys = [tuple(c.strip() for c in cells) for cells in good]
    if len(set(keys)) == len(keys):
        dataset["no_duplicate_rows"] = True
    return {"name": name, "columns": columns, "dataset": dataset}
