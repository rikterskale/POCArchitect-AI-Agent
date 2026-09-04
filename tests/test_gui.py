import re
import time
import webbrowser
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib.resources import files

import uvicorn
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from pocarchitect import cli
from pocarchitect.gui import GuiRuntime, create_app
from pocarchitect.service import AnalysisRequest, AnalysisService, AnalysisServiceError


class StubAnalysisService(AnalysisService):
    def execute(
        self, prepared, selected_files=None, event_sink=lambda _: None, **kwargs
    ):
        return super().execute(
            prepared,
            selected_files,
            event_sink,
            response_override="# GUI report\n\n### Finding\n- Severity: High\n",
        )


def authenticated_client(tmp_path):
    token = "test-session-token"
    app = create_app(
        session_token=token,
        port=8765,
        runtime=GuiRuntime(StubAnalysisService()),
    )
    client = TestClient(app, base_url="http://127.0.0.1:8765")
    response = client.get(f"/?token={token}", follow_redirects=True)
    assert response.status_code == 200
    return client


def test_gui_assets_preserve_csp_accessibility_and_responsive_contracts():
    web_root = files("pocarchitect") / "web"
    html = (web_root / "index.html").read_text(encoding="utf-8")
    css = (web_root / "styles.css").read_text(encoding="utf-8")
    javascript = (web_root / "app.js").read_text(encoding="utf-8")

    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids))
    targets = set()
    for attribute in ("aria-controls", "aria-describedby", "aria-labelledby", "for"):
        for value in re.findall(rf'\b{attribute}="([^"]+)"', html):
            targets.update(value.split())
    assert targets <= set(ids)
    assert '<script src="/assets/app.js" defer></script>' in html
    assert "<style" not in html
    assert "style=" not in html
    assert not re.search(r"\son[a-z]+=", html)
    assert "focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert css.count("@media (max-width:") >= 3
    assert 'role="tablist"' in html
    assert 'class="skip-link"' in html
    assert "sessionStorage" in javascript
    assert "requestSelectionEstimate" in javascript
    assert "recoverRun" in javascript
    assert 'id="run-demo"' in html
    assert 'id="refresh-providers"' in html
    assert "preferredProvider" in javascript
    assert "/api/demo" in javascript
    assert not re.search(r"(?:font(?:-size)?\s*:[^;]*\s)(?:8|9)px", css)


def test_gui_requires_launch_session_and_sets_security_headers():
    app = create_app(session_token="test-session-token", port=8765)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get("/api/bootstrap").status_code == 401
        response = client.get("/?token=test-session-token", follow_redirects=True)
        assert response.status_code == 200
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["cross-origin-opener-policy"] == "same-origin"
        assert "camera=()" in response.headers["permissions-policy"]
        assert client.get("/api/bootstrap").status_code == 200


def test_gui_rejects_unexpected_host_header():
    app = create_app(session_token="test-session-token", port=8765)
    with TestClient(app, base_url="http://attacker.example:8765") as client:
        response = client.get("/?token=test-session-token")

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid local host"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"


def test_gui_rejects_cross_origin_mutations(tmp_path):
    with authenticated_client(tmp_path) as client:
        response = client.post(
            "/api/preparations",
            json={"source": "https://example.com/advisory", "no_ingest": True},
            headers={"Origin": "https://malicious.example"},
        )

    assert response.status_code == 403


def test_gui_rejects_oversized_api_payload(tmp_path):
    with authenticated_client(tmp_path) as client:
        response = client.post(
            "/api/preparations",
            content=b"x" * 70_000,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://127.0.0.1:8765",
            },
        )

    assert response.status_code == 413
    assert response.json()["detail"] == "Request is too large"


def test_gui_rejects_invalid_source_with_actionable_detail(tmp_path):
    with authenticated_client(tmp_path) as client:
        response = client.post(
            "/api/preparations",
            json={"source": "", "provider": "local"},
            headers={"Origin": "http://127.0.0.1:8765"},
        )

    assert response.status_code == 422
    assert response.json()["detail"] == "A source URL or local directory is required"


def test_gui_prepare_approve_run_and_download(tmp_path):
    with authenticated_client(tmp_path) as client:
        prepared = client.post(
            "/api/preparations",
            json={
                "source": "https://example.com/advisory",
                "provider": "local",
                "no_ingest": True,
                "output_dir": str(tmp_path / "reports"),
            },
            headers={"Origin": "http://127.0.0.1:8765"},
        )
        assert prepared.status_code == 200
        preparation = prepared.json()
        assert preparation["files"] == []
        assert "system_prompt" not in preparation
        assert "grounding" not in preparation

        estimate = client.post(
            f"/api/preparations/{preparation['preparation_id']}/estimate",
            json={"selected_files": []},
            headers={"Origin": "http://127.0.0.1:8765"},
        )
        assert estimate.status_code == 200
        assert estimate.json()["files"] == 0
        assert estimate.json()["within_cost_limit"] is True

        started = client.post(
            "/api/runs",
            json={
                "preparation_id": preparation["preparation_id"],
                "selected_files": [],
            },
            headers={"Origin": "http://127.0.0.1:8765"},
        )
        assert started.status_code == 202
        job_id = started.json()["job_id"]

        for _ in range(100):
            job = client.get(f"/api/runs/{job_id}").json()
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)

        assert job["status"] == "completed", job
        result = job["result"]
        assert result["content"].startswith("# GUI report")
        download = client.get(f"/api/artifacts/{result['report_artifact_id']}/download")
        assert download.status_code == 200
        assert b"# GUI report" in download.content
        preview = client.get(f"/api/artifacts/{result['report_artifact_id']}")
        assert preview.status_code == 200
        assert preview.json()["content"].startswith("# GUI report")

        stream = client.get(
            f"/api/runs/{job_id}/events", headers={"Last-Event-ID": "not-a-number"}
        )
        assert stream.status_code == 200
        assert '"type": "finished"' in stream.text

        library = client.get("/api/reports").json()["reports"]
        assert any(
            report["artifact_id"] == result["report_artifact_id"] for report in library
        )

        reused = client.post(
            "/api/runs",
            json={"preparation_id": preparation["preparation_id"]},
            headers={"Origin": "http://127.0.0.1:8765"},
        )
        assert reused.status_code == 409
        assert client.get("/api/runs/missing").status_code == 404
        assert client.get("/api/artifacts/missing").status_code == 404


def test_gui_demo_reaches_a_report_without_source_provider_or_credential(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "pocarchitect.gui.default_output_dir", lambda: tmp_path / "reports"
    )
    monkeypatch.setattr(
        "pocarchitect.features.run_plugins",
        lambda *_: (_ for _ in ()).throw(
            AssertionError("demo must not run third-party analyzers")
        ),
    )
    token = "test-session-token"
    app = create_app(
        session_token=token,
        port=8765,
        runtime=GuiRuntime(AnalysisService()),
    )

    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get(f"/?token={token}", follow_redirects=True).status_code == 200
        started = client.post("/api/demo", headers={"Origin": "http://127.0.0.1:8765"})
        assert started.status_code == 202

        job_id = started.json()["job_id"]
        for _ in range(100):
            job = client.get(f"/api/runs/{job_id}").json()
            if job["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)

        assert job["status"] == "completed", job
        assert job["result"]["content"].startswith("# POCArchitect Demo Report")
        messages = [event["message"] for event in job["events"]]
        assert "Generating the demo locally. No provider request is made." in messages

        library = client.get("/api/reports").json()["reports"]
        assert any(
            report["artifact_id"] == job["result"]["report_artifact_id"]
            for report in library
        )


def test_gui_rejects_non_loopback_binding():
    try:
        create_app(session_token="token", host="0.0.0.0")
    except ValueError as error:
        assert "loopback" in str(error)
    else:
        raise AssertionError("Expected non-loopback binding to be rejected")


def test_gui_cli_uses_selected_loopback_port_without_opening_browser(monkeypatch):
    calls = []
    monkeypatch.setattr(
        uvicorn, "run", lambda application, **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(
        webbrowser,
        "open",
        lambda url: (_ for _ in ()).throw(AssertionError(f"opened browser: {url}")),
    )

    result = CliRunner().invoke(cli.app, ["gui", "--port", "9123", "--no-open"])

    assert result.exit_code == 0, result.stdout
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 9123,
            "access_log": False,
            "log_level": "warning",
            "server_header": False,
        }
    ]
    assert "http://127.0.0.1:9123/?token=" in result.stdout


def test_gui_expires_preparations_and_bounds_artifact_registry(tmp_path):
    runtime = GuiRuntime(StubAnalysisService())
    payload = type(
        "Payload",
        (),
        {
            "to_request": lambda self: AnalysisRequest(
                source="https://example.test/poc",
                provider="local",
                no_ingest=True,
                output_dir=str(tmp_path),
            )
        },
    )()
    view = runtime.prepare(payload)
    prepared = runtime._prepared[view["preparation_id"]]
    runtime._prepared[prepared.id] = replace(
        prepared,
        created_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
    )

    try:
        runtime.estimate(prepared.id, None)
    except AnalysisServiceError as error:
        assert "expired" in str(error)
    else:
        raise AssertionError("Expected an expired preparation to be rejected")

    from pocarchitect import gui

    for index in range(gui.MAX_RETAINED_ARTIFACTS + 5):
        path = tmp_path / f"artifact-{index}.md"
        path.write_text("# report\n", encoding="utf-8")
        runtime._register_artifact(path)
    runtime._purge_jobs()
    assert len(runtime._artifacts) == gui.MAX_RETAINED_ARTIFACTS
    runtime.close()


def test_gui_preview_reports_type_size_encoding_and_missing_file_errors(tmp_path):
    from pocarchitect import gui

    runtime = GuiRuntime(StubAnalysisService())
    app = create_app(session_token="token", port=8765, runtime=runtime)
    non_markdown = tmp_path / "report.json"
    oversized = tmp_path / "large.md"
    invalid = tmp_path / "invalid.md"
    missing = tmp_path / "missing.md"
    non_markdown.write_text("{}", encoding="utf-8")
    oversized.write_bytes(b"x" * (gui.MAX_REPORT_PREVIEW_BYTES + 1))
    invalid.write_bytes(b"\xff")
    missing.write_text("# gone\n", encoding="utf-8")
    artifact_ids = {
        name: runtime._register_artifact(path)
        for name, path in {
            "type": non_markdown,
            "size": oversized,
            "encoding": invalid,
            "missing": missing,
        }.items()
    }
    missing.unlink()

    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get("/?token=token", follow_redirects=True).status_code == 200
        assert client.get(f"/api/artifacts/{artifact_ids['type']}").status_code == 415
        assert client.get(f"/api/artifacts/{artifact_ids['size']}").status_code == 413
        assert (
            client.get(f"/api/artifacts/{artifact_ids['encoding']}").status_code == 415
        )
        assert (
            client.get(f"/api/artifacts/{artifact_ids['missing']}").status_code == 404
        )


def test_gui_rejects_empty_token_invalid_length_and_unlaunched_index():
    import pytest

    with pytest.raises(ValueError, match="session token"):
        create_app(session_token="")

    app = create_app(session_token="token", port=8765)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get("/").status_code == 401
        response = client.post(
            "/api/preparations",
            content=b"{}",
            headers={"Content-Length": "invalid"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid content length"


def test_gui_missing_event_stream_and_download_are_404(tmp_path):
    with authenticated_client(tmp_path) as client:
        assert client.get("/api/runs/missing/events").status_code == 404
        assert client.get("/api/artifacts/missing/download").status_code == 404


def test_gui_runtime_records_expected_and_unexpected_worker_failures(tmp_path):
    from pocarchitect import gui

    class FailingService(AnalysisService):
        def __init__(self, error):
            self.error = error

        def execute(self, *args, **kwargs):
            raise self.error

    prepared = AnalysisService().prepare(
        AnalysisRequest(
            source="https://example.test/source",
            provider="local",
            no_ingest=True,
            output_dir=str(tmp_path),
        )
    )

    for error, expected in (
        (AnalysisServiceError("expected failure"), "expected failure"),
        (RuntimeError("unexpected failure"), "failed unexpectedly"),
    ):
        runtime = GuiRuntime(FailingService(error))
        job = gui.GuiJob(id=f"job-{len(runtime._jobs)}")
        runtime._jobs[job.id] = job
        runtime._execute(job.id, prepared, None)
        snapshot = runtime.snapshot(job.id)
        assert snapshot["status"] == "failed"
        assert expected in snapshot["error"]
        runtime.close()


def test_gui_runtime_purges_expired_jobs_and_handles_missing_artifact_stats(
    tmp_path, monkeypatch
):
    from pocarchitect import gui

    runtime = GuiRuntime(StubAnalysisService())
    expired = gui.GuiJob(
        id="expired",
        status="completed",
        updated_at=(datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
    )
    runtime._jobs[expired.id] = expired
    runtime._purge_jobs()
    assert expired.id not in runtime._jobs

    path = tmp_path / "report.md"
    path.write_text("# report\n", encoding="utf-8")
    runtime._register_artifact(path)
    monkeypatch.setattr(gui, "MAX_RETAINED_ARTIFACTS", 0)
    monkeypatch.setattr(
        gui.Path,
        "stat",
        lambda self: (_ for _ in ()).throw(FileNotFoundError(self)),
    )
    runtime._purge_artifacts()
    assert runtime._artifacts == {}
    runtime.close()


def test_gui_report_preview_handles_file_disappearing_during_read(
    tmp_path, monkeypatch
):
    from pocarchitect import gui

    runtime = GuiRuntime(StubAnalysisService())
    report = tmp_path / "report.md"
    report.write_text("# report\n", encoding="utf-8")
    artifact_id = runtime._register_artifact(report)
    original_read_text = gui.Path.read_text

    def disappear(path, *args, **kwargs):
        if path == report:
            raise FileNotFoundError(path)
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(gui.Path, "read_text", disappear)
    app = create_app(session_token="token", port=8765, runtime=runtime)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        client.get("/?token=token", follow_redirects=True)
        response = client.get(f"/api/artifacts/{artifact_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Report is unavailable"


def test_gui_estimate_missing_preparation_is_conflict(tmp_path):
    with authenticated_client(tmp_path) as client:
        response = client.post(
            "/api/preparations/missing/estimate",
            json={"selected_files": []},
            headers={"Origin": "http://127.0.0.1:8765"},
        )
        assert response.status_code == 409


def test_gui_demo_worker_records_expected_and_unexpected_failures():
    from pocarchitect import gui

    class FailingPrepareService(AnalysisService):
        def __init__(self, error):
            self.error = error

        def prepare(self, *args, **kwargs):
            raise self.error

    for error, expected in (
        (AnalysisServiceError("expected demo failure"), "expected demo failure"),
        (RuntimeError("unexpected demo failure"), "failed unexpectedly"),
    ):
        runtime = GuiRuntime(FailingPrepareService(error))
        job = gui.GuiJob(id="demo")
        runtime._jobs[job.id] = job
        runtime._execute_demo(job.id)
        assert runtime.snapshot(job.id)["status"] == "failed"
        assert expected in runtime.snapshot(job.id)["error"]
        runtime.close()


def test_gui_runtime_bounds_terminal_jobs_and_ignores_unreadable_reports(
    tmp_path, monkeypatch
):
    from pocarchitect import gui

    runtime = GuiRuntime(StubAnalysisService())
    job = gui.GuiJob(id="retained", status="completed")
    runtime._jobs[job.id] = job
    monkeypatch.setattr(gui, "MAX_RETAINED_JOBS", 0)
    runtime._purge_jobs()
    assert runtime._jobs == {}

    report = tmp_path / "POCAnalysis_report.md"
    report.write_text("# report\n", encoding="utf-8")
    runtime._session_reports.add(report)
    monkeypatch.setattr(
        gui,
        "read_report_metadata",
        lambda path: (_ for _ in ()).throw(PermissionError("denied")),
    )
    assert runtime.reports() == []
    runtime.close()
