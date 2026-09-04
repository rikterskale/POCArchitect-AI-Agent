import importlib.util
import subprocess
import sys
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


def test_start_here_guide_has_the_complete_first_use_contract():
    validator = load_validator()

    assert validator.validate_start_guide(validator.START_GUIDE) == []


def test_platform_guide_reports_each_missing_contract_item(tmp_path):
    validator = load_validator()
    guide = tmp_path / "linux.md"
    guide.write_text("# Incomplete\n", encoding="utf-8")

    errors = validator.validate_guide("Linux", guide)

    assert any("validation status" in error for error in errors)
    assert any("canonical-guide link" in error for error in errors)
    assert any("command ledger" in error for error in errors)
    assert any("required platform delta" in error for error in errors)
    assert any("at least five" in error for error in errors)


def test_canonical_and_start_guides_report_missing_contracts(tmp_path):
    validator = load_validator()
    guide = tmp_path / "guide.md"
    guide.write_text("# Incomplete\n", encoding="utf-8")

    canonical_errors = validator.validate_canonical_guide(guide)
    start_errors = validator.validate_start_guide(guide)

    assert any("required heading" in error for error in canonical_errors)
    assert any("required command" in error for error in canonical_errors)
    assert any("safe example URL" in error for error in canonical_errors)
    assert any("success checks" in error for error in start_errors)
    assert any("troubleshooting matrix" in error for error in start_errors)
    assert any("local-only GUI warning" in error for error in start_errors)
