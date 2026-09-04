import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_documentation_commands.py"


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "validate_documentation_commands", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_selected_safe_documentation_commands_execute_without_network():
    assert load_validator().run_safe_probes() == []


def test_command_validator_detects_missing_documented_command():
    validator = load_validator()

    errors = validator.validate_documented_commands("")

    assert len(errors) == len(validator.DOCUMENTED_COMMANDS)


def test_command_validator_main_reports_success_and_failure(
    tmp_path, monkeypatch, capsys
):
    validator = load_validator()
    guide = tmp_path / "START_HERE.md"
    guide.write_text("\n".join(validator.DOCUMENTED_COMMANDS), encoding="utf-8")
    monkeypatch.setattr(validator, "GUIDE", guide)
    monkeypatch.setattr(validator, "run_safe_probes", lambda: [])
    monkeypatch.setattr(sys, "argv", ["validate_documentation_commands.py"])

    assert validator.main() == 0
    assert "Credential-free documentation commands passed" in capsys.readouterr().out

    monkeypatch.setattr(validator, "run_safe_probes", lambda: ["failed probe"])
    assert validator.main() == 1
    assert "failed probe" in capsys.readouterr().out


def test_safe_probe_validator_reports_command_and_protocol_failures(monkeypatch):
    validator = load_validator()
    monkeypatch.setattr(
        validator.RUNNER,
        "invoke",
        lambda *args, **kwargs: SimpleNamespace(exit_code=1, stdout="failed"),
    )
    errors = validator.run_safe_probes()
    assert any("exited 1" in error for error in errors)
    assert any("Help probe failed" in error for error in errors)
    assert any("Non-interactive setup" in error for error in errors)
    assert any("Safe batch-reset probe failed" in error for error in errors)


def test_safe_probe_validator_handles_invalid_json_without_crashing(monkeypatch):
    validator = load_validator()

    def invoke(app, arguments):
        if arguments in (["--help"], ["gui", "--help"]):
            return SimpleNamespace(exit_code=0, stdout="Usage: ok")
        if arguments[-1] == "setup":
            return SimpleNamespace(exit_code=2, stdout='{"event": "error"}')
        return SimpleNamespace(exit_code=0, stdout="{")

    monkeypatch.setattr(validator.RUNNER, "invoke", invoke)
    errors = validator.run_safe_probes()
    assert any("Safe probe emitted invalid JSON" in error for error in errors)
    assert any("batch-reset probe emitted invalid JSON" in error for error in errors)
