import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_novice_guides_pass_their_command_ledger_validator():
    result = subprocess.run(
        [sys.executable, "scripts/validate_novice_guides.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
