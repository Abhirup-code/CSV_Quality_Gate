"""Property-based tests: Hypothesis generates thousands of random tables and checks rules that must
always hold, which finds edge cases that hand-written examples miss."""
import csv
import io

from hypothesis import given, settings
from hypothesis import strategies as st

from qualitygate.checks import read_csv, run_checks
from qualitygate.infer import infer_rules
from qualitygate.report import summarize
from qualitygate.rules import validate_rules

cell = st.one_of(
    st.text(max_size=12),
    st.integers(-1000, 1000).map(str),
    st.floats(allow_nan=True, allow_infinity=True).map(str),
    st.dates().map(str),
    st.sampled_from(["", " ", "West", "South", "1_000", "٣", "2026-1-5"]),
)


@st.composite
def tables(draw):
    width = draw(st.integers(1, 5))
    header = draw(st.lists(st.text(min_size=1, max_size=8), min_size=width, max_size=width))
    rows = draw(st.lists(st.lists(cell, min_size=width, max_size=width), max_size=30))
    return header, rows


def round_trip(header, rows, tmp_path):
    """Write the table as a real CSV file and read it back, the way the tool sees it."""
    buffer = io.StringIO()
    csv.writer(buffer).writerows([header, *rows])
    path = tmp_path / "t.csv"
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return read_csv(path)


@settings(max_examples=400, deadline=None)
@given(tables())
def test_any_file_passes_the_rules_inferred_from_it(tmp_path_factory, table):
    header, rows = round_trip(*table, tmp_path_factory.mktemp("p"))
    rules = validate_rules(infer_rules(header, rows))
    assert run_checks(header, rows, rules) == []


@settings(max_examples=300, deadline=None)
@given(tables())
def test_summary_counts_always_add_up(tmp_path_factory, table):
    header, rows = round_trip(*table, tmp_path_factory.mktemp("s"))
    rules = {"columns": {header[0]: {"type": "int", "required": True, "unique": True}}}
    issues = run_checks(header, rows, rules)
    s = summarize(issues, len(rows))
    assert s["errors"] + s["warnings"] == len(issues)
    assert 0 <= s["rows_with_errors"] <= s["total_rows"]
    assert 0.0 <= s["row_pass_rate"] <= 100.0
    assert s["status"] == ("FAIL" if s["errors"] else "PASS")
