import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_documentation_links.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_documentation_links", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_documentation_links_are_valid():
    result = subprocess.run(
        [sys.executable, "scripts/validate_documentation_links.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_link_validator_includes_prompt_and_both_documentation_reports():
    paths = {
        path.relative_to(ROOT).as_posix() for path in load_validator().markdown_files()
    }

    assert "pocarchitect/POC_Architect_Prompt.md" in paths
    assert "docs/DOCUMENTATION_GAP_ANALYSIS.md" in paths
    assert "docs/DOCUMENTATION_REVIEW_REPORT.md" in paths


def test_link_validator_rejects_targets_outside_repository(tmp_path):
    validator = load_validator()
    root = validator.ROOT
    page = root / "docs" / "escape-test.md"
    page.write_text("[escape](/etc/passwd)\n", encoding="utf-8")
    try:
        errors = validator.validate_file(page)
    finally:
        page.unlink()

    assert any("escapes repository" in error for error in errors)


def test_link_validator_handles_nested_parentheses_and_ignores_code(tmp_path):
    validator = load_validator()
    validator.ROOT = tmp_path
    destination = tmp_path / "target (draft).md"
    destination.write_text("# Real heading\n", encoding="utf-8")
    source = tmp_path / "source.md"
    source.write_text(
        "[valid](target%20(draft).md#real-heading)\n" "`[not-a-link](missing.md)`\n",
        encoding="utf-8",
    )

    assert validator.validate_file(source) == []
