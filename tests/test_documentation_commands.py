import importlib.util
from pathlib import Path

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
