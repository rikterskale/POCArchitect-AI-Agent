import pytest

from pocarchitect import cli
from pocarchitect.service import AnalysisRequest, AnalysisService, AnalysisServiceError


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
