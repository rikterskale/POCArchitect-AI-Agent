import json
from datetime import datetime
import os

import pytest
from rich.console import Console

from pocarchitect import features
from pocarchitect import security
from pocarchitect.security import extract_dependencies


def test_project_config_round_trip_and_nearest_lookup(tmp_path, monkeypatch):
    config = features.write_project_config(tmp_path / features.CONFIG_FILE)
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    values, resolved = features.load_project_config()

    assert resolved == config
    assert values["provider"] == "xai"
    assert values["include_mitigations"] is True


def test_mock_report_contains_architecture_and_mitigations():
    report = features.mock_report("pypi:demo", "High", "Linux", True)

    assert "```mermaid" in report
    assert "## Findings" in report
    assert "## Mitigations" in report


def test_report_history_diff_export_and_scaffold(tmp_path):
    previous = tmp_path / "previous.md"
    current = tmp_path / "current.md"
    previous.write_text(
        "# Report\n\n### Finding A\n- Severity: Low\n", encoding="utf-8"
    )
    current.write_text(
        "# Report\n\n### Finding A\n- Severity: High\n", encoding="utf-8"
    )

    assert "Severity: High" in features.report_diff(previous, current)
    html = features.export_report(current, "html")
    pdf = features.export_report(current, "pdf")
    structured = features.export_report(current, "json")
    assert "<!doctype html>" in html.read_text(encoding="utf-8")
    assert pdf.read_bytes().startswith(b"%PDF-1.4")
    assert (
        json.loads(structured.read_text(encoding="utf-8"))["metrics"]["findings_count"]
        == 1
    )

    created = features.create_scaffold(current, tmp_path / "blueprint")
    assert any(path.name == "pyproject.toml" for path in created)
    assert all(path.exists() for path in created)


def test_source_classification_covers_broader_inputs(tmp_path):
    assert features.classify_source(str(tmp_path)) == "local-directory"
    assert features.classify_source("pypi:requests") == "pypi-package"
    assert features.classify_source("npm:react") == "npm-package"
    assert features.classify_source("docker:alpine:latest") == "docker-image"
    assert (
        features.classify_source("https://example.test/source.tar.gz") == "archive-url"
    )


def test_dependency_extraction_requires_exact_versions():
    packages = extract_dependencies(
        "requests==2.32.0\nflask>=3.0\nclick~=8.1\nold<=1.0\n"
        '{"dependencies":{"react":"18.3.1","loose":"^1.0.0"}}'
    )

    assert {tuple(item.values()) for item in packages} == {
        ("PyPI", "requests", "2.32.0"),
        ("npm", "react", "18.3.1"),
    }


def test_history_recovers_from_valid_non_object_json(tmp_path):
    report = tmp_path / "POCAnalysis_test.md"
    report.write_text("# Report\n", encoding="utf-8")
    (tmp_path / features.HISTORY_FILE).write_text("[]", encoding="utf-8")

    features.update_history(tmp_path, report)

    rows = features.history_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["path"] == str(report)


def test_history_filters_malformed_rows(tmp_path):
    (tmp_path / features.HISTORY_FILE).write_text(
        json.dumps({"reports": ["bad", {"path": "good.md"}]}), encoding="utf-8"
    )

    assert features.history_rows(tmp_path) == [{"path": "good.md"}]


def test_plugin_registration_and_failure_isolation(monkeypatch):
    class GoodPlugin:
        name = "good"

        def analyze(self, source, grounding):
            return f"{source}:{grounding}"

    class BadPlugin:
        name = "bad"

        def analyze(self, source, grounding):
            raise RuntimeError("plugin failure")

    monkeypatch.setattr(features, "_PLUGINS", {})
    monkeypatch.setattr(features, "_PLUGINS_DISCOVERED", True)
    features.register_plugin(GoodPlugin())
    features.register_plugin(BadPlugin())

    assert features.registered_plugins() == ["bad", "good"]
    assert features.run_plugins("source", "grounding") == ["source:grounding"]
    with pytest.raises(ValueError, match="non-empty name"):
        features.register_plugin(type("Unnamed", (), {"name": ""})())
    with pytest.raises(TypeError, match="protocol contract"):
        features.AnalyzerPlugin.analyze(object(), "source", "grounding")


def test_osv_query_normalizes_results(monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "results": [
                        {
                            "vulns": [
                                {
                                    "id": "OSV-1",
                                    "aliases": ["CVE-1"],
                                    "summary": "example",
                                }
                            ]
                        }
                    ]
                }
            ).encode()

    monkeypatch.setattr(security, "urlopen", lambda request, timeout: Response())
    packages = [{"ecosystem": "PyPI", "name": "demo", "version": "1.0.0"}]

    assert security.query_osv(packages) == [
        {
            **packages[0],
            "id": "OSV-1",
            "aliases": ["CVE-1"],
            "summary": "example",
        }
    ]


def test_osv_query_rejects_malformed_response(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"[]"

    monkeypatch.setattr(security, "urlopen", lambda request, timeout: Response())

    with pytest.raises(ValueError, match="invalid batch response"):
        security.query_osv([{"ecosystem": "PyPI", "name": "demo", "version": "1.0.0"}])


def test_scan_path_reads_supported_manifests(monkeypatch, tmp_path):
    (tmp_path / "requirements.txt").write_text("demo==1.0.0\n", encoding="utf-8")
    monkeypatch.setattr(security, "query_osv", lambda packages: [{"id": "OSV-1"}])

    packages, findings = security.scan_path(tmp_path)

    assert packages == [{"ecosystem": "PyPI", "name": "demo", "version": "1.0.0"}]
    assert findings == [{"id": "OSV-1"}]


def test_summary_card_and_dashboard_render_observable_results(tmp_path):
    console = Console(record=True, width=120)
    report = tmp_path / "report.md"
    content = "# Report\n\n### Finding A\n- Severity: High\n- Upgrade dependency\n"

    features.render_summary_card(console, content, report, 0.0123)
    features.render_dashboard(
        console,
        {"grounding": 0.25},
        ["app.py"],
        content,
    )
    rendered = console.export_text()

    assert "Run complete" in rendered
    assert "0.0123" in rendered
    assert str(report.resolve()) in rendered
    assert "grounding" in rendered
    assert "app.py" in rendered
    assert "Finding A" in rendered


def test_render_dashboard_handles_empty_progress_and_url_only_input():
    console = Console(record=True, width=100)

    features.render_dashboard(console, {}, [], "")

    rendered = console.export_text()
    assert "Starting" in rendered
    assert "URL-only input" in rendered


def test_find_previous_report_returns_newest_matching_report(tmp_path):
    source = "https://example.test/source"
    older = tmp_path / "POCAnalysis_older.md"
    newer = tmp_path / "POCAnalysis_newer.md"
    unrelated = tmp_path / "POCAnalysis_unrelated.md"
    for path, value in ((older, source), (newer, source), (unrelated, "other")):
        path.write_text(
            f'---\nsource_url: "{value}"\n---\n# Report\n', encoding="utf-8"
        )
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    assert features.find_previous_report(tmp_path, source) == newer
    assert features.find_previous_report(tmp_path, "missing") is None


def test_utc_now_returns_timezone_aware_iso_timestamp():
    parsed = datetime.fromisoformat(features.utc_now())

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None
