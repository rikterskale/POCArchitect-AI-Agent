from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docker_alias_supports_interactive_confirmation():
    guide = (ROOT / "docs" / "docker-guide.md").read_text(encoding="utf-8")

    assert "alias pocarch='docker run --rm -it " in guide
    assert "pocarch-preview" in guide


def test_slow_marker_does_not_claim_default_exclusion():
    pytest_config = (ROOT / "pytest.ini").read_text(encoding="utf-8")

    assert "included unless the invocation applies a marker filter" in pytest_config
    assert "skipped BY default" not in pytest_config


def test_manifest_packages_documentation_navigation_targets():
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

    assert "recursive-include docs *.md" in manifest
    assert "prune docs" not in manifest
    assert "include POCArchitect_Quickstart.txt" in manifest
    assert "include .github/workflows/ci.yml" in manifest
