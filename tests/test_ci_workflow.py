import importlib.util
import sys
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

    assert any("jobs mapping" in error for error in errors)


def test_ci_validator_rejects_malformed_yaml(tmp_path):
    validator = load_validator()
    workflow = tmp_path / validator.WORKFLOW
    workflow.parent.mkdir(parents=True)
    workflow.write_text("jobs: [unterminated\n", encoding="utf-8")

    errors = validator.validate(tmp_path)

    assert any("not valid YAML" in error for error in errors)


def test_ci_validator_does_not_count_commented_controls(tmp_path):
    validator = load_validator()
    workflow = tmp_path / validator.WORKFLOW
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "jobs:\n  quality:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      # - run: ruff check --output-format=github .\n"
        "      - run: echo safe\n",
        encoding="utf-8",
    )

    errors = validator.validate(tmp_path)

    assert any("Ruff" not in error and "ruff check" in error for error in errors)


def test_ci_validator_main_reports_success_and_failure(monkeypatch, capsys):
    validator = load_validator()
    monkeypatch.setattr(sys, "argv", ["validate_ci_workflow.py"])
    monkeypatch.setattr(validator, "validate", list)
    assert validator.main() == 0
    assert "Canonical CI workflow is valid YAML" in capsys.readouterr().out

    monkeypatch.setattr(validator, "validate", lambda: ["broken"])
    assert validator.main() == 1
    assert "broken" in capsys.readouterr().out


def test_ci_validator_reports_missing_workflow_and_retired_mutator(tmp_path):
    validator = load_validator()
    assert validator.validate(tmp_path) == [
        f"Missing canonical workflow: {validator.WORKFLOW}"
    ]

    workflow = tmp_path / validator.WORKFLOW
    workflow.parent.mkdir(parents=True)
    workflow.write_text("jobs: {}\n", encoding="utf-8")
    retired = tmp_path / validator.RETIRED_MUTATORS[0]
    retired.parent.mkdir(parents=True, exist_ok=True)
    retired.touch()

    assert any("Retired mutating" in error for error in validator.validate(tmp_path))
