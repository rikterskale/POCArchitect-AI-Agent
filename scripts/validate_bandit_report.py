#!/usr/bin/env python3
"""Reject incomplete or finding-bearing Bandit JSON reports.

Bandit has historically returned success for some internal scanner errors. This
small gate ensures CI cannot mistake a partial scan for a clean result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_report(path: Path) -> list[str]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"Bandit report is missing or invalid: {error}"]
    if not isinstance(payload, dict):
        return ["Bandit report root must be a JSON object"]

    errors = payload.get("errors")
    findings = payload.get("results")
    if not isinstance(errors, list) or not isinstance(findings, list):
        return ["Bandit report must contain list-valued errors and results fields"]

    failures = [f"Bandit could not scan a file: {item}" for item in errors]
    for item in findings:
        if not isinstance(item, dict):
            failures.append("Bandit returned a malformed finding")
            continue
        filename = item.get("filename", "unknown file")
        line = item.get("line_number", "?")
        test_id = item.get("test_id", "unknown check")
        severity = item.get("issue_severity", "unknown severity")
        failures.append(f"{severity} {test_id} at {filename}:{line}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    failures = validate_report(args.report)
    if failures:
        print("Bandit security validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print("Bandit completed without scanner errors or findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
