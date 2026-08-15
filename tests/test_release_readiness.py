"""Run the new-user release readiness gate as part of the test suite.

The gate script (`scripts/release_readiness.py`) is the single source of truth
for the five-pillar standard. This test drives it end to end so the standard is
enforced locally and in CI, not just in the dedicated wheel-install CI job.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.release_readiness import COVERED_OPTIONS, all_long_options

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "release_readiness.py"


def test_option_inventory_is_scoped_by_command():
    options = all_long_options()

    assert ("root", "--output-dir") in options
    assert ("preflight", "--output-dir") in options
    assert ("root", "--output-dir") in COVERED_OPTIONS
    assert ("preflight", "--output-dir") in COVERED_OPTIONS


@pytest.fixture(scope="module")
def gate_report():
    """Run the gate once and share its JSON report across the readiness tests."""
    result = subprocess.run(
        [sys.executable, str(GATE), "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return result.returncode, json.loads(result.stdout)


@pytest.mark.readiness
def test_release_readiness_gate_passes(gate_report):
    returncode, report = gate_report

    # Surface exactly which pillar/check failed instead of a bare exit code.
    failed = [
        f"{pillar['title']}: {check['name']} ({check['detail']})"
        for pillar in report["pillars"]
        for check in pillar["checks"]
        if not check["passed"]
    ]
    message = "Release readiness gate failed:\n" + "\n".join(failed)
    assert report["ready"] and returncode == 0, message


@pytest.mark.readiness
def test_release_readiness_reports_all_five_pillars(gate_report):
    _, report = gate_report
    keys = {pillar["key"] for pillar in report["pillars"]}
    assert keys == {
        "installation",
        "troubleshooting",
        "features",
        "recovery",
        "documentation",
    }
