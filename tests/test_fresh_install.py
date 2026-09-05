import importlib.util
import subprocess
import sys
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
    wheel = tmp_path / "pocarchitect-0.3.0-py3-none-any.whl"
    wheel.touch()

    assert validator.select_artifact(tmp_path, "wheel") == wheel.resolve()

    (tmp_path / "duplicate.whl").touch()
    with pytest.raises(ValueError, match="exactly one wheel"):
        validator.select_artifact(tmp_path, "wheel")


def test_select_artifact_keeps_wheel_and_sdist_checks_separate(tmp_path):
    validator = load_validator()
    sdist = tmp_path / "pocarchitect-0.3.0.tar.gz"
    sdist.touch()

    assert validator.select_artifact(tmp_path, "sdist") == sdist.resolve()


def test_main_reports_subprocess_failure_without_traceback(
    tmp_path, monkeypatch, capsys
):
    validator = load_validator()
    artifact = tmp_path / "pocarchitect.whl"
    artifact.touch()
    monkeypatch.setattr(sys, "argv", ["validate_fresh_install.py", str(tmp_path)])
    monkeypatch.setattr(
        validator,
        "run",
        lambda command, **kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(1, command)
        ),
    )

    assert validator.main() == 1
    assert "Clean wheel install failed" in capsys.readouterr().out


def test_venv_python_run_clean_environment_and_successful_main(
    tmp_path, monkeypatch, capsys
):
    validator = load_validator()
    artifact = tmp_path / "pocarchitect.whl"
    artifact.touch()
    venv = tmp_path / "venv"
    expected_name = "python.exe" if sys.platform.startswith("win") else "python"
    assert validator.venv_python(venv).name == expected_name

    subprocess_calls = []
    monkeypatch.setattr(
        validator.subprocess,
        "run",
        lambda command, **kwargs: subprocess_calls.append((command, kwargs)),
    )
    validator.run(["tool", "--version"], cwd=tmp_path, env={"SAFE": "1"})
    assert subprocess_calls[0][1]["check"] is True

    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("PYTHONPATH", "unsafe")
    clean = validator.clean_environment()
    assert "OPENAI_API_KEY" not in clean and "PYTHONPATH" not in clean
    assert clean["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"

    run_calls = []
    monkeypatch.setattr(
        validator, "run", lambda command, **kwargs: run_calls.append(command)
    )
    monkeypatch.setattr(sys, "argv", ["validate_fresh_install.py", str(tmp_path)])
    assert validator.main() == 0
    assert len(run_calls) == 5
    assert "passed the first-run readiness gate" in capsys.readouterr().out


def test_windows_venv_path_and_missing_artifact_parser_error(tmp_path, monkeypatch):
    validator = load_validator()
    assert (
        validator.venv_python(tmp_path, platform="win32")
        == tmp_path / "Scripts" / "python.exe"
    )

    monkeypatch.setattr(sys, "argv", ["validate_fresh_install.py", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        validator.main()
    assert error.value.code == 2
