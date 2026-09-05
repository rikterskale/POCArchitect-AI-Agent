#!/usr/bin/env python3
"""Check read-only CI invariants without rewriting repository files."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path(".github/workflows/ci.yml")
RETIRED_MUTATORS = (
    Path("scripts/apply_ci_fixes.py"),
    Path("scripts/apply_ci_fixes.template.py"),
    Path("scripts/repair_apply_ci_fixes.py"),
)
REQUIRED_JOBS = {
    "quality",
    "test",
    "windows-test",
    "security",
    "docker",
    "package",
    "release-readiness",
    "build",
}
REQUIRED_RUN_COMMANDS = (
    "ruff check --output-format=github .",
    "black --check --diff .",
    "mypy pocarchitect tests",
    "python scripts/generate_docs.py --check",
    "python scripts/validate_novice_guides.py",
    "python scripts/validate_documentation_links.py",
    "python scripts/validate_documentation_commands.py",
    "python scripts/validate_documentation_reports.py",
    "python scripts/validate_ci_workflow.py",
    "python scripts/validate_fresh_install.py dist --artifact",
    "pytest --cov=pocarchitect --cov-report=xml",
    "pytest -q tests/test_cli.py::test_windows_help_uses_plain_renderer_for_redirected_output",
    "python -m playwright install --with-deps chromium",
    "pip-audit",
    "python scripts/validate_bandit_report.py bandit-report.json",
    "docker build -t pocarchitect:test .",
    "python -m pocarchitect --format json --no-color verify run tests/fixtures/verified-poc --yes",
    "result['status'] == 'verified'",
    "result['sandbox']['network'] == 'none'",
    "result['sandbox']['capabilities_dropped'] == ['ALL']",
    "python -m build",
    "python scripts/validate_distribution.py dist",
)
REQUIRED_ACTIONS = {"actions/upload-artifact@v7", "actions/download-artifact@v8"}


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    workflow = root / WORKFLOW
    if not workflow.exists():
        return [f"Missing canonical workflow: {WORKFLOW}"]

    try:
        document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        return [f"Canonical workflow is not valid YAML: {error}"]
    if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
        return ["Canonical workflow must define a jobs mapping"]

    jobs = document["jobs"]
    for job in sorted(REQUIRED_JOBS - set(jobs)):
        errors.append(f"Canonical workflow is missing job `{job}`")

    steps = [
        step
        for job in jobs.values()
        if isinstance(job, dict) and isinstance(job.get("steps"), list)
        for step in job["steps"]
        if isinstance(step, dict)
    ]
    run_text = "\n".join(str(step.get("run", "")) for step in steps)
    actions = {str(step["uses"]) for step in steps if "uses" in step}
    for command in REQUIRED_RUN_COMMANDS:
        if command not in run_text:
            errors.append(f"Canonical workflow is missing run command `{command}`")
    for action in sorted(REQUIRED_ACTIONS - actions):
        errors.append(f"Canonical workflow is missing action `{action}`")

    serialized = repr(document)
    for value in (
        "windows-latest",
        "macos-latest",
        "3.10",
        "3.14",
        "wheel",
        "sdist",
    ):
        if value not in serialized:
            errors.append(f"Canonical workflow is missing matrix value `{value}`")
    for name, job in jobs.items():
        if isinstance(job, dict) and not isinstance(job.get("timeout-minutes"), int):
            errors.append(
                f"Canonical CI job `{name}` must set an integer timeout-minutes"
            )
    for retired in RETIRED_MUTATORS:
        if (root / retired).exists():
            errors.append(
                f"Retired mutating CI utility must remain absent: {retired.as_posix()}"
            )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("CI workflow invariant validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Canonical CI workflow is valid YAML and required jobs, commands, actions, "
        "and matrix values are present; this does not establish hosted-job success."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
