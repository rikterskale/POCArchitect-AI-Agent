import re
import time
import webbrowser
from importlib.resources import files

import uvicorn
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from pocarchitect import cli
from pocarchitect.gui import GuiRuntime, create_app
from pocarchitect.service import AnalysisService


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

        reused = client.post(
            "/api/runs",
            json={"preparation_id": preparation["preparation_id"]},
            headers={"Origin": "http://127.0.0.1:8765"},
        )
        assert reused.status_code == 409


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
