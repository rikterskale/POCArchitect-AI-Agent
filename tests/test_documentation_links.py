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
