import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_ci_workflow.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_ci_workflow", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_ci_workflow_passes_read_only_invariants():
    assert load_validator().validate(ROOT) == []


def test_retired_ci_mutators_are_absent():
    validator = load_validator()

    assert all(not (ROOT / path).exists() for path in validator.RETIRED_MUTATORS)


def test_ci_validator_detects_a_missing_required_control(tmp_path):
    validator = load_validator()
    workflow = tmp_path / validator.WORKFLOW
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: incomplete\n", encoding="utf-8")

    errors = validator.validate(tmp_path)

    assert any("quality:" in error for error in errors)
