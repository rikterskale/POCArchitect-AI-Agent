from pathlib import Path

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def test_release_workflow_builds_validates_attests_and_publishes_tagged_artifacts():
    text = WORKFLOW.read_text(encoding="utf-8")
    document = yaml.safe_load(text)

    assert isinstance(document, dict)
    assert 'tags: ["v*.*.*"]' in text
    assert "GITHUB_REF_NAME" in text
    assert "pyproject.toml" in text
    assert "python -m build" in text
    assert "validate_distribution.py dist" in text
    assert "--artifact wheel" in text
    assert "--artifact sdist" in text
    assert "sha256sum *.whl *.tar.gz > SHA256SUMS" in text
    assert "actions/attest-build-provenance@v3" in text
    assert "id-token: write" in text
    assert "attestations: write" in text
    assert "gh release create" in text
    assert "--verify-tag" in text
    assert "contents: write" in text
    assert text.count("timeout-minutes:") == 2


def test_dependabot_covers_python_actions_and_container_dependencies():
    config = yaml.safe_load((ROOT / ".github" / "dependabot.yml").read_text())

    ecosystems = {entry["package-ecosystem"] for entry in config["updates"]}
    assert ecosystems == {"pip", "github-actions", "docker"}
