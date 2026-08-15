import subprocess
import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_novice_guides.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_novice_guides", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_novice_guides_pass_their_command_ledger_validator():
    result = subprocess.run(
        [sys.executable, "scripts/validate_novice_guides.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_platform_supplements_are_valid_as_concise_deltas():
    validator = load_validator()

    for platform, path in validator.GUIDES.items():
        assert validator.validate_guide(platform, path) == []
        assert path.read_text(encoding="utf-8").count("\n## ") < 10
