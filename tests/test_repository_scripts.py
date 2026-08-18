import shutil
import subprocess
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _usable_bash() -> str | None:
    """Ignore the Windows WSL launcher when no Bash runtime is installed."""
    bash = shutil.which("bash")
    if bash and os.name == "nt" and Path(bash).parent.name.lower() == "system32":
        return None
    return bash


BASH = _usable_bash()


def test_no_network_verifier_uses_offline_preflight_and_safe_batch_fixture():
    script = (ROOT / "verify.sh").read_text(encoding="utf-8")
    logical_lines = script.replace("\\\n", " ").splitlines()
    offline_commands = [
        line.strip()
        for line in logical_lines
        if line.strip().startswith(("pocarchitect --url", "pocarchitect --batch"))
    ]

    assert "pocarchitect preflight --offline" in script
    assert "example_usage/dry_run_batch_urls.txt" in script
    assert len(offline_commands) == 3
    assert all("--no-ingest" in command for command in offline_commands)
    assert "production-ready" not in script


def test_real_provider_script_checks_openai_and_refuses_placeholder_fixtures():
    script = (ROOT / "test-full.sh").read_text(encoding="utf-8")

    assert "pocarchitect preflight --provider openai" in script
    assert 'REAL_BATCH_FILE="${1:-}"' in script
    assert 'REAL_BATCH_PATH="$(canonical_path "$REAL_BATCH_FILE")"' in script
    assert "Refusing placeholder fixture" in script
    assert 'pocarchitect --batch "$REAL_BATCH_PATH"' in script


@pytest.mark.skipif(BASH is None, reason="Bash is required for shell-script checks")
@pytest.mark.parametrize(
    "batch_argument",
    [
        "./example_usage/batch_urls.txt",
        str((ROOT / "example_usage" / "batch_urls.txt").resolve()),
        "./example_usage/dry_run_batch_urls.txt",
        str((ROOT / "example_usage" / "dry_run_batch_urls.txt").resolve()),
    ],
)
def test_real_provider_script_refuses_equivalent_placeholder_paths(batch_argument):
    result = subprocess.run(
        [BASH, "test-full.sh", batch_argument],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 2
    assert "Refusing placeholder fixture for a billable provider run" in result.stdout


def test_batch_template_is_prominently_labeled_and_separate_from_safe_fixture():
    real_template = (ROOT / "example_usage" / "batch_urls.txt").read_text(
        encoding="utf-8"
    )
    dry_run_fixture = (ROOT / "example_usage" / "dry_run_batch_urls.txt").read_text(
        encoding="utf-8"
    )

    assert real_template.startswith("# TEMPLATE ONLY:")
    assert "billable provider" in real_template
    assert "--no-ingest --dry-run" in dry_run_fixture
