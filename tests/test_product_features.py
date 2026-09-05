import json
import os
import stat
from datetime import datetime
from pathlib import Path

import pytest
from rich.console import Console

from pocarchitect import features, security
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


def test_scaffold_materializes_a_strict_implementation_bundle(tmp_path):
    report = tmp_path / "report.md"
    report.write_text(
        "# Report\n\n"
        "## Implementation Bundle\n\n"
        "### File: pyproject.toml\n"
        '```toml\n[project]\nname = "lab-poc"\nversion = "1.0.0"\n```\n\n'
        "### File: src/lab_poc.py\n"
        "```python\ndef prove(value: int) -> bool:\n    return value == 42\n```\n\n"
        "### File: tests/test_acceptance.py\n"
        "```python\nimport unittest\n\nclass TestPoC(unittest.TestCase):\n"
        "    def test_lab_behavior(self):\n        self.assertTrue(True)\n```\n\n"
        "## Mitigations\n",
        encoding="utf-8",
    )
    output = tmp_path / "working-candidate"

    created = features.create_scaffold(report, output)

    assert (
        (output / "src" / "lab_poc.py")
        .read_text(encoding="utf-8")
        .startswith("def prove")
    )
    assert (output / "tests" / "test_acceptance.py").is_file()
    contract = json.loads(
        (output / ".pocarchitect" / "poc-verification.json").read_text(encoding="utf-8")
    )
    assert contract["implementation_status"] == "draft"
    assert contract["test_commands"]
    assert any(path.name == "poc-verification.json" for path in created)


def test_scaffold_rejects_implementation_path_traversal_before_writing(tmp_path):
    report = tmp_path / "report.md"
    report.write_text(
        "## Implementation Bundle\n\n"
        "### File: ../../outside.py\n```python\nprint('unsafe')\n```\n",
        encoding="utf-8",
    )
    output = tmp_path / "candidate"

    with pytest.raises(ValueError, match="Unsafe implementation bundle path"):
        features.create_scaffold(report, output)

    assert not output.exists()


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated Windows rights")
def test_scaffold_does_not_follow_a_generated_file_symlink(tmp_path):
    report = tmp_path / "report.md"
    report.write_text(
        "## Implementation Bundle\n\n"
        "### File: src/poc.py\n```python\nprint('candidate')\n```\n",
        encoding="utf-8",
    )
    output = tmp_path / "candidate"
    (output / "src").mkdir(parents=True)
    victim = tmp_path / "victim.py"
    victim.write_text("keep = True\n", encoding="utf-8")
    (output / "src" / "poc.py").symlink_to(victim)

    with pytest.raises(ValueError, match="cannot replace a symlink"):
        features.create_scaffold(report, output)

    assert victim.read_text(encoding="utf-8") == "keep = True\n"


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated Windows rights")
def test_scaffold_rejects_a_symlinked_control_directory_before_writing(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("# Report\n", encoding="utf-8")
    output = tmp_path / "candidate"
    output.mkdir()
    control_target = tmp_path / "control-target"
    control_target.mkdir()
    (output / ".pocarchitect").symlink_to(control_target, target_is_directory=True)

    with pytest.raises(ValueError, match="cannot traverse a symlink"):
        features.create_scaffold(report, output)

    assert list(output.iterdir()) == [output / ".pocarchitect"]
    assert list(control_target.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated Windows rights")
def test_report_derived_writes_replace_symlinks_without_touching_their_targets(
    tmp_path,
):
    report = tmp_path / "report.md"
    report.write_text("# Report\n", encoding="utf-8")
    victim = tmp_path / "victim.txt"
    victim.write_text("do not replace", encoding="utf-8")

    export = report.with_suffix(".json")
    export.symlink_to(victim)
    features.export_report(report, "json")
    assert not export.is_symlink()
    assert victim.read_text(encoding="utf-8") == "do not replace"

    history = tmp_path / features.HISTORY_FILE
    history.symlink_to(victim)
    features.update_history(tmp_path, report)
    assert not history.is_symlink()
    assert victim.read_text(encoding="utf-8") == "do not replace"


def test_source_classification_covers_broader_inputs(tmp_path):
    local_file = tmp_path / "artifact.bin"
    local_file.write_bytes(b"x")
    assert features.classify_source(str(tmp_path)) == "local-directory"
    assert features.classify_source(str(local_file)) == "local-file"
    assert features.classify_source("pypi:requests") == "pypi-package"
    assert features.classify_source("npm:react") == "npm-package"
    assert features.classify_source("docker:alpine:latest") == "docker-image"
    assert (
        features.classify_source("https://example.test/source.tar.gz") == "archive-url"
    )
    assert features.classify_source("https://example.test/source") == "download-url"
    assert features.classify_source("CVE-2026-0001") == "identifier"


def test_architecture_diagram_classifies_all_supported_file_groups():
    diagram = features.architecture_diagram(
        ["Dockerfile", "app.py", "tests/test_app.py", "README.md"]
    )

    assert "Configuration / runtime" in diagram
    assert "Application / PoC logic" in diagram
    assert "Validation" in diagram
    assert "Documentation" in diagram
    assert "Source material" in features.architecture_diagram([])


def test_dependency_extraction_requires_exact_versions():
    packages = extract_dependencies(
        "requests==2.32.0\nflask>=3.0\nclick~=8.1\nold<=1.0\n"
        '{"dependencies":{"react":"18.3.1","loose":"^1.0.0"}}'
    )

    assert {tuple(item.values()) for item in packages} == {
        ("PyPI", "requests", "2.32.0"),
        ("npm", "react", "18.3.1"),
    }

    assert extract_dependencies('serde = { version = "1.0.203" }') == [
        {"ecosystem": "crates.io", "name": "serde", "version": "1.0.203"}
    ]


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


def test_history_and_metadata_recover_from_malformed_content(tmp_path, monkeypatch):
    assert features.history_rows(tmp_path) == []
    history = tmp_path / features.HISTORY_FILE
    history.write_text("not json", encoding="utf-8")
    assert features.history_rows(tmp_path) == []
    history.write_text(json.dumps({"reports": "bad"}), encoding="utf-8")
    assert features.history_rows(tmp_path) == []

    report = tmp_path / "POCAnalysis_test.md"
    report.write_text("---\ncomment\nraw: not-json\n---\n# Report\n", encoding="utf-8")
    assert features.read_report_metadata(report) == {"raw": "not-json"}

    history.write_text("not json", encoding="utf-8")
    features.update_history(tmp_path, report)
    assert len(features.history_rows(tmp_path)) == 1

    history.write_text(json.dumps({"reports": "bad"}), encoding="utf-8")
    features.update_history(tmp_path, report)
    assert len(features.history_rows(tmp_path)) == 1

    monkeypatch.setattr(
        features,
        "read_report_metadata",
        lambda path: (_ for _ in ()).throw(PermissionError("denied")),
    )
    assert features.find_previous_report(tmp_path, "source") is None


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


def test_plugin_discovery_loads_classes_and_isolates_broken_entries(monkeypatch):
    class Plugin:
        name = "loaded"

        def analyze(self, source, grounding):
            return "ok"

    class EntryPoint:
        def __init__(self, value):
            self.value = value

        def load(self):
            if isinstance(self.value, Exception):
                raise self.value
            return self.value

    monkeypatch.setattr(features, "_PLUGINS", {})
    monkeypatch.setattr(features, "_PLUGINS_DISCOVERED", False)
    monkeypatch.setattr(
        features,
        "entry_points",
        lambda **kwargs: [EntryPoint(Plugin), EntryPoint(RuntimeError("broken"))],
    )

    assert features.registered_plugins() == ["loaded"]
    assert features.registered_plugins() == ["loaded"]


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


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"results": []}, "result count"),
        ({"results": [None]}, "invalid package result"),
        ({"results": [{"vulns": [None]}]}, "invalid vulnerability record"),
    ],
)
def test_osv_query_rejects_incomplete_or_malformed_records(
    monkeypatch, payload, message
):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    monkeypatch.setattr(security, "urlopen", lambda request, timeout: Response())

    with pytest.raises(ValueError, match=message):
        security.query_osv([{"ecosystem": "PyPI", "name": "demo", "version": "1.0.0"}])


def test_osv_query_with_no_packages_does_not_call_network(monkeypatch):
    monkeypatch.setattr(
        security,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network called")),
    )

    assert security.query_osv([]) == []


def test_scan_path_reads_supported_manifests(monkeypatch, tmp_path):
    (tmp_path / "requirements.txt").write_text("demo==1.0.0\n", encoding="utf-8")
    monkeypatch.setattr(security, "query_osv", lambda packages: [{"id": "OSV-1"}])

    packages, findings = security.scan_path(tmp_path)

    assert packages == [{"ecosystem": "PyPI", "name": "demo", "version": "1.0.0"}]
    assert findings == [{"id": "OSV-1"}]


def test_scan_path_skips_unreadable_manifest(monkeypatch, tmp_path):
    manifest = tmp_path / "requirements.txt"
    manifest.write_text("demo==1.0.0\n", encoding="utf-8")
    original_read_text = security.Path.read_text

    def fail_selected_file(path, *args, **kwargs):
        if path == manifest:
            raise PermissionError("denied")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(security.Path, "read_text", fail_selected_file)
    monkeypatch.setattr(security, "query_osv", lambda packages: [])

    assert security.scan_path(tmp_path) == ([], [])


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
    resolved = str(report.resolve())
    assert resolved in rendered or str(Path.cwd()) in rendered
    assert "grounding" in rendered
    assert "app.py" in rendered
    assert "Finding A" in rendered


def test_live_dashboard_lifecycle(monkeypatch):
    updates = []

    class FakeLive:
        def __init__(self, layout, **kwargs):
            updates.append("created")

        def start(self):
            updates.append("started")

        def update(self, layout, refresh):
            updates.append("updated")

        def stop(self):
            updates.append("stopped")

    monkeypatch.setattr(features, "Live", FakeLive)
    dashboard = features.LiveRunDashboard(Console(), enabled=True)
    dashboard.start()
    dashboard.phase("grounding")
    dashboard.phase("grounding", complete=True)
    dashboard.set_files(["app.py"])
    dashboard.set_report("# Report")
    dashboard.stop()

    assert updates[0:2] == ["created", "started"]
    assert updates.count("updated") >= 5
    assert updates[-1] == "stopped"

    disabled = features.LiveRunDashboard(Console(), enabled=False)
    disabled.start()
    disabled.phase("ignored")
    disabled.stop()


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


def test_export_rejects_unknown_format(tmp_path):
    report = tmp_path / "report.md"
    report.write_text("# Report\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported report format"):
        features.export_report(report, "docx")


def test_utc_now_returns_timezone_aware_iso_timestamp():
    parsed = datetime.fromisoformat(features.utc_now())

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None


def test_project_config_parses_numeric_and_unquoted_scalars(tmp_path, monkeypatch):
    config = tmp_path / features.CONFIG_FILE
    config.write_text(
        "[defaults]\n" "count = 3\n" "ratio = 1.5\n" "label = unquoted\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    values, resolved = features.load_project_config()

    assert resolved == config
    assert values["count"] == 3
    assert values["ratio"] == 1.5
    assert values["label"] == "unquoted"


def test_pdf_export_wraps_long_lines(tmp_path):
    report = tmp_path / "long.md"
    report.write_text("# Report\n\n" + ("A" * 200) + "\n", encoding="utf-8")

    pdf = features.export_report(report, "pdf")

    assert pdf.read_bytes().startswith(b"%PDF-1.4")
    assert pdf.stat().st_size > 200
    if os.name != "nt":
        assert stat.S_IMODE(pdf.stat().st_mode) == 0o600
