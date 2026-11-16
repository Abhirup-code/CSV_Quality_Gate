"""Comparing a run with an earlier one."""
import json

from qualitygate.cli import main
from qualitygate.trend import compare_runs, describe, read_baseline

RULES = {"columns": {"amount": {"type": "int", "required": True}}}


def run(tmp_path, body, name, **flags):
    """Check a one-column CSV and return (exit code, stdout+stderr)."""
    csv = tmp_path / f"{name}.csv"
    csv.write_text("amount\n" + body)
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps(RULES))
    argv = [str(csv), "--rules", str(rules), "--out", str(tmp_path / name)]
    for flag, value in flags.items():
        argv.append(f"--{flag.replace('_', '-')}")
        if value is not True:
            argv.append(str(value))
    return main(argv)


def summary(**fields):
    return {"status": "FAIL", "errors": 4, "warnings": 1, "row_pass_rate": 90.0,
            "by_rule": {"type": 4}, **fields}


def test_fewer_errors_is_not_worse():
    diff = compare_runs(summary(errors=9, by_rule={"type": 9}), summary())
    assert diff["worse"] is False
    assert diff["errors"] == (9, 4)
    assert "errors 9 to 4" in describe(diff)


def test_more_errors_is_worse():
    diff = compare_runs(summary(), summary(errors=9, by_rule={"type": 9}))
    assert diff["worse"] is True


def test_a_rule_broken_for_the_first_time_is_worse_even_at_the_same_count():
    before = summary(errors=4, by_rule={"type": 4})
    after = summary(errors=4, by_rule={"type": 2, "required": 2})
    diff = compare_runs(before, after)
    assert diff["worse"] is True and diff["new_rules"] == {"required": 2}
    assert "newly broken: required (2)" in describe(diff)


def test_a_rule_that_stopped_breaking_is_named():
    before = summary(by_rule={"type": 2, "unique": 2})
    diff = compare_runs(before, summary(by_rule={"type": 2}))
    assert diff["fixed_rules"] == ["unique"] and diff["worse"] is False
    assert "no longer broken: unique" in describe(diff)


def test_a_run_that_used_to_pass_is_worse_even_with_errors_tolerated():
    """--max-error-rate can keep the status at PASS; falling off that is still a regression."""
    before = summary(status="PASS", errors=0, by_rule={})
    diff = compare_runs(before, summary(status="FAIL"))
    assert diff["worse"] is True


def test_no_change_reads_as_no_change():
    assert describe(compare_runs(summary(), summary())) == "Compared with the baseline: no change."


def test_the_comparison_is_printed_and_does_not_change_the_exit_code(tmp_path, capsys):
    assert run(tmp_path, "1\n2\n", "first") == 0
    assert run(tmp_path, "1\nx\n", "second", baseline=tmp_path / "first") == 1
    assert "newly broken: type (1)" in capsys.readouterr().out
    # The data improved, so the run passes even though the baseline failed.
    assert run(tmp_path, "1\n2\n", "third", baseline=tmp_path / "second") == 0


def test_fail_on_worse_fails_a_run_that_would_otherwise_pass(tmp_path, capsys):
    assert run(tmp_path, "1\n2\n", "first") == 0
    code = run(tmp_path, "1\n2\n3\n", "second", baseline=tmp_path / "first",
               max_error_rate=100, fail_on_worse=True)
    assert code == 0  # same clean data, nothing got worse
    code = run(tmp_path, "x\n2\n", "third", baseline=tmp_path / "first",
               max_error_rate=100, fail_on_worse=True)
    assert code == 1
    assert "PASS" in capsys.readouterr().out  # the gate itself tolerated the bad row


def test_a_missing_baseline_says_so_and_passes(tmp_path, capsys):
    assert run(tmp_path, "1\n2\n", "only", baseline=tmp_path / "nowhere", fail_on_worse=True) == 0
    assert "nothing to compare" in capsys.readouterr().err


def test_a_damaged_baseline_is_ignored(tmp_path):
    for text in ["", "{}", "not json", '{"summary": null}', '{"summary": {"status": "PASS"}}']:
        path = tmp_path / "report.json"
        path.write_text(text)
        assert read_baseline(path) is None
    path.write_text(json.dumps({"summary": summary()}))
    assert read_baseline(path)["errors"] == 4


def test_each_file_in_a_run_finds_its_own_baseline(tmp_path, capsys):
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps(RULES))
    good, bad = tmp_path / "good.csv", tmp_path / "bad.csv"
    good.write_text("amount\n1\n")
    bad.write_text("amount\n1\n")
    args = [str(good), str(bad), "--rules", str(rules)]
    assert main([*args, "--out", str(tmp_path / "before")]) == 0
    bad.write_text("amount\nx\n")
    assert main([*args, "--out", str(tmp_path / "after"), "--baseline", str(tmp_path / "before")]) == 1
    out = capsys.readouterr().out
    assert out.count("Compared with the baseline") == 2
    assert "no change" in out and "newly broken: type (1)" in out
