import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_documentation_links_are_valid():
    result = subprocess.run(
        [sys.executable, "scripts/validate_documentation_links.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
