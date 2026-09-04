import pytest

from pocarchitect import cli
from pocarchitect.service import (
    AnalysisRequest,
    AnalysisService,
    AnalysisServiceError,
    provider_configuration,
)


def test_service_prepares_metadata_without_exposing_source_content(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text(
        "OPENAI_API_KEY=sk-test-1234567890abcdef\nprint('ok')\n"
    )
    events = []

    prepared = AnalysisService().prepare(
        AnalysisRequest(
            source=str(source),
            local_path=str(source),
            provider="local",
            output_dir=str(tmp_path / "reports"),
        ),
        events.append,
    )
    view = prepared.public_view()

    assert view["ingestion"] == "local-directory"
    assert view["files"] == [
        {
            "path": "app.py",
            "bytes": (source / "app.py").stat().st_size,
            "included": True,
        }
    ]
    assert view["total_bytes"] == (source / "app.py").stat().st_size
    assert view["redaction_count"] >= 1
    assert "sk-test" not in str(view)
    assert [event["event"] for event in events][-1] == "preparation_ready"


def test_service_executes_selected_grounding_and_writes_report(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('app')\n", encoding="utf-8")
    (source / "README.md").write_text("# docs\n", encoding="utf-8")
    events = []
    service = AnalysisService()
    prepared = service.prepare(
        AnalysisRequest(
            source=str(source),
            local_path=str(source),
            provider="local",
            output_dir=str(tmp_path / "reports"),
        )
    )

    result = service.execute(
        prepared,
        ["app.py"],
        events.append,
        response_override="# Result\n\n### Finding\n- Severity: High\n",
    )

    assert result.report_path.is_file()
    assert result.grounding_files == ("app.py",)
    assert "```mermaid" in result.content
    assert events[-1]["event"] == "run_complete"


def test_service_recalculates_metadata_for_selected_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('app')\n", encoding="utf-8")
    (source / "README.md").write_text("# docs\n", encoding="utf-8")
    service = AnalysisService()
    prepared = service.prepare(
        AnalysisRequest(
            source=str(source),
            local_path=str(source),
            provider="local",
            output_dir=str(tmp_path / "reports"),
        )
    )

    estimate = service.estimate_selection(prepared, ["app.py"])

    assert estimate["files"] == 1
    assert estimate["total_bytes"] == (source / "app.py").stat().st_size
    assert estimate["estimated_tokens"] > 0
    assert estimate["within_cost_limit"] is True


def test_service_rejects_unknown_file_selection(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
    service = AnalysisService()
    prepared = service.prepare(
        AnalysisRequest(
            source=str(source),
            local_path=str(source),
            provider="local",
            output_dir=str(tmp_path / "reports"),
        )
    )

    with pytest.raises(AnalysisServiceError, match="Unknown grounding file"):
        service.execute(prepared, ["outside.py"], response_override="# Result")


def test_event_capture_is_context_local_and_suppresses_console(monkeypatch):
    captured = []
    printed = []
    monkeypatch.setattr(
        cli.console, "print", lambda *args, **kwargs: printed.append(args)
    )

    with cli.capture_events(captured.append):
        cli.emit("example", "message", value=1)

    assert captured == [{"event": "example", "message": "message", "value": 1}]
    assert printed == []


def test_provider_configuration_picks_up_a_new_key_without_gui_restart(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert provider_configuration()["openai"] is False

    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=test-key-added-after-launch\n", encoding="utf-8"
    )

    assert provider_configuration()["openai"] is True


@pytest.mark.parametrize(
    ("analysis_request", "message"),
    [
        (AnalysisRequest(source="x", provider="unknown"), "Unsupported provider"),
        (AnalysisRequest(source="x", provider="local", model=" "), "model name"),
        (
            AnalysisRequest(source="x", provider="local", temperature=-0.1),
            "Temperature",
        ),
        (AnalysisRequest(source="x", provider="local", temperature=2.1), "Temperature"),
        (
            AnalysisRequest(source="x", provider="local", max_estimated_cost=-1),
            "cannot be negative",
        ),
        (
            AnalysisRequest(source="x", provider="local", report_format="docx"),
            "report format",
        ),
        (AnalysisRequest(source="", provider="local"), "source URL"),
        (
            AnalysisRequest(source="x", provider="local", base_url="not-a-url"),
            "complete http",
        ),
    ],
)
def test_service_rejects_invalid_requests(analysis_request, message):
    with pytest.raises(AnalysisServiceError, match=message):
        AnalysisService().normalize_request(analysis_request)


def test_service_rejects_missing_local_directory(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(AnalysisServiceError, match="Local source directory not found"):
        AnalysisService().normalize_request(
            AnalysisRequest(
                source=str(missing), local_path=str(missing), provider="local"
            )
        )


def test_service_reports_ingestion_failure_before_preparation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        cli,
        "build_grounding_context",
        lambda *args, **kwargs: cli.GroundingResult(
            "WARNING: Ingestion failed.", "url-only-ingestion-failed"
        ),
    )

    with pytest.raises(AnalysisServiceError, match="Source ingestion failed"):
        AnalysisService().prepare(
            AnalysisRequest(
                source="https://github.com/example/missing",
                provider="local",
                output_dir=str(tmp_path),
            )
        )


def test_service_optional_outputs_and_vulnerability_failure(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "requirements.txt").write_text("requests==2.32.0\n", encoding="utf-8")
    output = tmp_path / "reports"
    service = AnalysisService()
    request = AnalysisRequest(
        source=str(source),
        local_path=str(source),
        provider="local",
        output_dir=str(output),
        report_format="json",
        vulnerability_scan=True,
        scaffold=True,
    )
    events = []
    prepared = service.prepare(request)
    monkeypatch.setattr(
        "pocarchitect.security.query_osv",
        lambda packages: (_ for _ in ()).throw(OSError("offline")),
    )

    result = service.execute(
        prepared,
        event_sink=events.append,
        response_override="# Result\n\n### Finding\n- Severity: High\n",
    )

    assert result.export_path.suffix == ".json" and result.export_path.is_file()
    assert (output / f"{cli.slugify(str(source))}-blueprint").is_dir()
    assert any(event["event"] == "vulnerability_scan_failed" for event in events)
    assert any(event["event"] == "scaffold_created" for event in events)


def test_service_rejects_prepared_prompt_above_safe_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("pocarchitect.service.MAX_PROMPT_CHARACTERS", 10)

    with pytest.raises(AnalysisServiceError, match="Prepared prompt exceeds"):
        AnalysisService().prepare(
            AnalysisRequest(
                source="https://example.test/advisory",
                provider="local",
                no_ingest=True,
                output_dir=str(tmp_path),
            )
        )
