"""Automated UAT for docs/USER_JOURNEY.md journey-map rows J1–J22 and B1–B3."""

from __future__ import annotations

import json
import sys
import time

import pytest
import typer
import uvicorn
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from pocarchitect import cli
from pocarchitect.gui import GuiRuntime, create_app
from pocarchitect.service import AnalysisService

RUNNER = CliRunner()


def test_uat_j1_help_exits_zero_after_install():
    result = RUNNER.invoke(cli.app, ["--help"])
    assert result.exit_code == 0
    assert "quickstart" in result.stdout


def test_uat_j2_version_prints_product_banner():
    result = RUNNER.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "POCArchitect v" in result.stdout


def test_uat_j3_offline_preflight_passes_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = RUNNER.invoke(
        cli.app, ["preflight", "--offline", "--format", "json", "--no-color"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["event"] == "preflight"
    assert payload["message"] == "Preflight passed."


def test_uat_j4_j5_quickstart_writes_demo_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = RUNNER.invoke(cli.app, ["--format", "json", "--no-color", "quickstart"])
    assert result.exit_code == 0, result.stdout
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert any(event["event"] == "preflight" for event in events)
    assert any(event["event"] == "report_saved" for event in events)
    reports = list((tmp_path / "reports" / "demo").glob("POCAnalysis_*.md"))
    assert reports
    body = reports[0].read_text(encoding="utf-8")
    assert "POCArchitect Demo Report" in body


def test_uat_j6_json_dry_run_has_preview():
    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://github.com/example/poc",
            "--no-ingest",
            "--dry-run",
            "--format",
            "json",
            "--no-color",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["event"] == "dry_run"
    assert "report_preview" in payload


def test_uat_j7_gui_no_open_prints_launch_url(monkeypatch):
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: None)
    result = RUNNER.invoke(cli.app, ["gui", "--port", "9123", "--no-open"])
    assert result.exit_code == 0, result.stdout
    assert "http://127.0.0.1:9123/" in result.stdout
    assert "?token=" in result.stdout


def test_uat_j8_gui_index_requires_launch_session():
    app = create_app(session_token="uat-token", port=8765)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        response = client.get("/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Open the GUI from its launch URL"


def test_uat_j9_j10_gui_demo_and_report_library(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pocarchitect.gui.default_output_dir", lambda: tmp_path / "reports"
    )
    app = create_app(
        session_token="uat-token",
        port=8765,
        runtime=GuiRuntime(AnalysisService()),
    )
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get("/?token=uat-token", follow_redirects=True).status_code == 200
        started = client.post("/api/demo", headers={"Origin": "http://127.0.0.1:8765"})
        assert started.status_code == 202
        job_id = started.json()["job_id"]
        job = None
        for _ in range(100):
            job = client.get(f"/api/runs/{job_id}").json()
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        assert job is not None
        assert job["status"] == "completed", job
        assert "POCArchitect Demo Report" in job["result"]["content"]
        library = client.get("/api/reports").json()["reports"]
        assert library
        artifact = client.get(
            f"/api/artifacts/{job['result']['report_artifact_id']}"
        ).json()
        assert "POCArchitect Demo Report" in artifact["content"]


def test_uat_j11_invalid_github_url():
    result = RUNNER.invoke(cli.app, ["--url", "https://github.com/owner", "--dry-run"])
    assert result.exit_code == 2
    assert "Invalid PoC URL" in result.stdout


def test_uat_j12_missing_source():
    result = RUNNER.invoke(cli.app, ["--dry-run"])
    assert result.exit_code == 2
    assert "Provide --url, --source, --path, or --batch" in result.stdout


def test_uat_j13_url_and_batch_together(tmp_path):
    batch = tmp_path / "batch.txt"
    batch.write_text("https://example.test/a\n", encoding="utf-8")
    result = RUNNER.invoke(
        cli.app, ["--url", "https://example.test/a", "--batch", str(batch), "--dry-run"]
    )
    assert result.exit_code == 2
    assert "Provide either --url or --batch, not both" in result.stdout


def test_uat_j14_ingestion_failure_before_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_prompt", lambda: "system")
    monkeypatch.setattr(
        cli,
        "build_grounding_context",
        lambda *args, **kwargs: cli.GroundingResult(
            "WARNING: Ingestion failed.", "url-only-ingestion-failed"
        ),
    )
    monkeypatch.setattr(
        cli,
        "get_llm_response",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("provider called")),
    )
    events = []
    with cli.capture_events(events.append), pytest.raises(typer.Exit) as error:
        cli.process_single_url(
            url="https://github.com/example/missing",
            provider="openai",
            api_key="unused",
            model="gpt-4o",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path,
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=False,
        )
    assert error.value.exit_code == 2
    assert any(
        "Source ingestion failed; no provider call was made" in event["message"]
        for event in events
    )


def test_uat_j15_confirmation_required_without_yes(tmp_path, monkeypatch):
    source = tmp_path / "src"
    source.mkdir()
    (source / "app.py").write_text("print(1)\n", encoding="utf-8")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    events = []
    with cli.capture_events(events.append), pytest.raises(typer.Exit) as error:
        cli.process_single_url(
            url=str(source),
            provider="local",
            api_key=None,
            model="model",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path / "reports",
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=False,
            local_path=source,
            confirmed=False,
        )
    assert error.value.exit_code == 2
    assert any(
        "Confirmation is required in non-interactive mode" in event["message"]
        for event in events
    )


def test_uat_j16_cost_limit_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_prompt", lambda: "system prompt")
    events = []
    with cli.capture_events(events.append), pytest.raises(typer.Exit) as error:
        cli.process_single_url(
            url="https://example.test/poc",
            provider="openai",
            api_key=None,
            model="gpt-4o",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path,
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=True,
            max_estimated_cost=0.0,
        )
    assert error.value.exit_code == 2
    assert any("exceeds the" in event["message"] for event in events)


def test_uat_j17_setup_requires_tty(monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    result = RUNNER.invoke(cli.app, ["setup"])
    assert result.exit_code == 2
    assert "Setup is interactive" in result.stdout


def test_uat_j18_gui_requires_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "uvicorn", None)
    result = RUNNER.invoke(cli.app, ["gui", "--no-open"])
    assert result.exit_code == 2
    assert "The GUI dependencies are not installed" in result.stdout


def test_uat_j19_workflow_status_missing_state(tmp_path):
    result = RUNNER.invoke(
        cli.app, ["workflow-status", "--state", str(tmp_path / "missing.json")]
    )
    assert result.exit_code == 2
    assert "Workflow state not found" in result.stdout


def test_uat_j20_compare_requires_two_sources():
    result = RUNNER.invoke(cli.app, ["compare", "only-one"])
    assert result.exit_code == 2
    assert "Compare requires at least two sources" in result.stdout


def test_uat_j21_publish_requires_gh(tmp_path, monkeypatch):
    report = tmp_path / "report.md"
    report.write_text("# Report\n", encoding="utf-8")
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    result = RUNNER.invoke(cli.app, ["publish", str(report)])
    assert result.exit_code == 2
    assert "GitHub CLI is required for publishing" in result.stdout


def test_uat_j22_init_refuses_existing_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    first = RUNNER.invoke(cli.app, ["init"])
    second = RUNNER.invoke(cli.app, ["init"])
    assert first.exit_code == 0
    assert second.exit_code == 2
    assert "Use --force to replace it" in second.stdout


def test_uat_b1_empty_batch_file(tmp_path):
    batch = tmp_path / "empty.txt"
    batch.write_text("# comments only\n", encoding="utf-8")
    events = []
    with cli.capture_events(events.append), pytest.raises(typer.Exit) as error:
        cli.process_batch_file(
            batch_path=batch,
            provider="local",
            api_key=None,
            model="model",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path,
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=True,
            dry_run=True,
        )
    assert error.value.exit_code == 2
    assert any(
        "Batch file is empty or contains no valid URLs" in event["message"]
        for event in events
    )


def test_uat_b2_confirm_scope_is_not_a_workflow_command(tmp_path):
    state = tmp_path / "workflow.json"
    assert (
        RUNNER.invoke(cli.app, ["workflow-init", "--state", str(state)]).exit_code == 0
    )
    result = RUNNER.invoke(
        cli.app,
        [
            "workflow-apply",
            "--state",
            str(state),
            "--command",
            "confirm_scope",
            "--payload",
            "{}",
        ],
    )
    assert result.exit_code == 2
    assert "Unsupported workflow command" in result.stdout


def test_uat_b3_no_mitigations_in_dry_run_prompt():
    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://github.com/example/poc",
            "--no-ingest",
            "--dry-run",
            "--no-mitigations",
            "--format",
            "json",
            "--no-color",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert "Include Mitigations: No" in payload["prompt"]
