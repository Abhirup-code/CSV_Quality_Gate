"""Compare a run with an earlier one, so a pipeline can tell improving data from rotting data.

A single run only says pass or fail. With --max-error-rate a file can fail the same way every day
and nobody notices it getting worse, or fix half its rows and get no credit for it. This reads the
report.json of an earlier run and says what moved.
"""
import json


def read_baseline(path):
    """The summary from an earlier report.json, or None when there is nothing usable there."""
    try:
        with open(path, encoding="utf-8") as f:
            summary = json.load(f)["summary"]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return None
    return summary if isinstance(summary, dict) and "errors" in summary else None


def compare_runs(before, after):
    """What changed between two runs of the same rules."""
    was, now = before.get("by_rule", {}), after.get("by_rule", {})
    new_rules = {rule: count for rule, count in now.items() if rule not in was}
    fixed_rules = sorted(rule for rule in was if rule not in now)
    errors = (before.get("errors", 0), after.get("errors", 0))
    status = (before.get("status", "?"), after.get("status", "?"))
    return {
        "status": status,
        "errors": errors,
        "warnings": (before.get("warnings", 0), after.get("warnings", 0)),
        "row_pass_rate": (before.get("row_pass_rate"), after.get("row_pass_rate")),
        "new_rules": new_rules,
        "fixed_rules": fixed_rules,
        # More errors, a rule broken that was clean before, or a run that used to pass.
        "worse": errors[1] > errors[0]
        or bool(new_rules)
        or (status[0] == "PASS" and status[1] == "FAIL"),
    }


def _moved(name, pair):
    return None if pair[0] == pair[1] else f"{name} {pair[0]} to {pair[1]}"


def describe(diff):
    """One line for the console: what got better, what got worse."""
    parts = [
        part
        for part in (
            _moved("errors", diff["errors"]),
            _moved("warnings", diff["warnings"]),
            _moved("row pass rate", tuple(f"{v}%" for v in diff["row_pass_rate"])),
        )
        if part
    ]
    if diff["fixed_rules"]:
        parts.append("no longer broken: " + ", ".join(diff["fixed_rules"]))
    if diff["new_rules"]:
        parts.append(
            "newly broken: "
            + ", ".join(f"{rule} ({count})" for rule, count in sorted(diff["new_rules"].items()))
        )
    return "Compared with the baseline: " + ("; ".join(parts) if parts else "no change") + "."
