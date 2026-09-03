import json

from pocarchitect import features
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
        'requests==2.32.0\n{"dependencies":{"react":"18.3.1","loose":"^1.0.0"}}'
    )

    assert {tuple(item.values()) for item in packages} == {
        ("PyPI", "requests", "2.32.0"),
        ("npm", "react", "18.3.1"),
    }
