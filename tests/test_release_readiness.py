"""Run the new-user release readiness gate as part of the test suite.

The gate script (`scripts/release_readiness.py`) is the single source of truth
for the six-pillar standard. This test drives it end to end so the standard is
enforced locally and in CI, not just in the dedicated wheel-install CI job.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.release_readiness import (
    COVERED_OPTIONS,
    Check,
    Pillar,
    all_long_options,
    cli_result_detail,
    console_executable_path,
    json_events,
    pillar_installation,
    render_text,
    run_completion_probe,
    run_console,
)

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "release_readiness.py"


def test_option_inventory_is_scoped_by_command():
    options = all_long_options()

    assert ("root", "--output-dir") in options
    assert ("preflight", "--output-dir") in options
    assert ("root", "--output-dir") in COVERED_OPTIONS
    assert ("preflight", "--output-dir") in COVERED_OPTIONS


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX virtualenv Python executables are symlinks",
)
def test_console_executable_stays_in_symlinked_virtualenv(tmp_path):
    base_python = tmp_path / "base" / "bin" / "python"
    base_python.parent.mkdir(parents=True)
    base_python.touch()
    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(base_python)

    assert console_executable_path(venv_python) == venv_python.parent / "pocarchitect"


def test_completion_probe_does_not_require_parent_shell(tmp_path, monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)

    result = run_completion_probe(tmp_path)

    assert result.returncode == 0, result.stderr
    assert "_completion" in result.stdout


def test_text_renderer_reports_check_details_and_overall_failure():
    pillar = Pillar("example", "Example")
    pillar.checks = [Check("working", True), Check("broken", False, "reason")]

    rendered = render_text([pillar])

    assert "[FAIL] Example" in rendered
    assert "ok working" in rendered
    assert "XX broken  (reason)" in rendered
    assert "RESULT: NOT READY" in rendered


def test_console_runner_missing_and_present_executable(tmp_path, monkeypatch):
    executable = tmp_path / "pocarchitect"
    monkeypatch.setattr(
        "scripts.release_readiness.console_executable_path", lambda value: executable
    )
    missing = run_console(["--version"], tmp_path)
    assert missing.returncode == 127
    assert "not found" in missing.stderr

    executable.touch()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "ok", ""),
    )
    assert run_console(["--version"], tmp_path).stdout == "ok"


def test_json_event_parser_ignores_blank_and_invalid_lines():
    assert json_events('\nnot-json\n{"event": "ok"}\n') == [{"event": "ok"}]


def test_cli_result_detail_is_bounded_and_keeps_the_error_tail():
    result = subprocess.CompletedProcess([], 2, "x" * 300, "prefix fatal error")

    detail = cli_result_detail(result, max_stream_chars=20)

    assert "exit=2" in detail
    assert "…" in detail
    assert "fatal error" in detail
    assert len(detail) < 100


def test_installation_pillar_records_entry_point_discovery_failure(
    tmp_path, monkeypatch
):
    success = subprocess.CompletedProcess(
        [], 0, '{"message":"Preflight passed."}\n', ""
    )
    monkeypatch.setattr(
        "scripts.release_readiness.run_cli", lambda *args, **kwargs: success
    )
    monkeypatch.setattr(
        "importlib.metadata.entry_points",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("metadata unavailable")),
    )
    monkeypatch.setattr(
        "scripts.release_readiness.run_completion_probe", lambda work: success
    )

    pillar = pillar_installation(tmp_path)

    assert any(
        check.name == "`pocarchitect` console script registered" and not check.passed
        for check in pillar.checks
    )


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
        check=False,
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
def test_release_readiness_reports_all_six_pillars(gate_report):
    _, report = gate_report
    keys = {pillar["key"] for pillar in report["pillars"]}
    assert keys == {
        "installation",
        "troubleshooting",
        "features",
        "recovery",
        "documentation",
        "guided-workflow",
    }
