import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_fresh_install.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_fresh_install", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_select_artifact_requires_exactly_one_matching_distribution(tmp_path):
    validator = load_validator()
    wheel = tmp_path / "pocarchitect-0.2.0-py3-none-any.whl"
    wheel.touch()

    assert validator.select_artifact(tmp_path, "wheel") == wheel.resolve()

    (tmp_path / "duplicate.whl").touch()
    with pytest.raises(ValueError, match="exactly one wheel"):
        validator.select_artifact(tmp_path, "wheel")


def test_select_artifact_keeps_wheel_and_sdist_checks_separate(tmp_path):
    validator = load_validator()
    sdist = tmp_path / "pocarchitect-0.2.0.tar.gz"
    sdist.touch()

    assert validator.select_artifact(tmp_path, "sdist") == sdist.resolve()
    with pytest.raises(ValueError, match="found 0"):
        validator.select_artifact(tmp_path, "wheel")
