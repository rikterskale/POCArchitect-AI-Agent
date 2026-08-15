#!/usr/bin/env python3
"""Check read-only CI invariants without rewriting repository files."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path(".github/workflows/ci.yml")
RETIRED_MUTATORS = (
    Path("scripts/apply_ci_fixes.py"),
    Path("scripts/apply_ci_fixes.template.py"),
    Path("scripts/repair_apply_ci_fixes.py"),
)
REQUIRED_SNIPPETS = (
    "  quality:",
    "  test:",
    "  security:",
    "  docker:",
    "  build:",
    "ruff check --output-format=github .",
    "ruff format --check .",
    "black --check --diff .",
    "mypy pocarchitect tests",
    "python scripts/generate_docs.py --check",
    "python scripts/validate_novice_guides.py",
    "python scripts/validate_documentation_links.py",
    "python scripts/validate_documentation_commands.py",
    "python scripts/validate_documentation_reports.py",
    "python scripts/validate_ci_workflow.py",
    "pytest --cov=pocarchitect --cov-report=xml",
    "pip-audit",
    "docker build -t pocarchitect:test .",
    "python -m build",
    "python scripts/validate_distribution.py dist",
)


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    workflow = root / WORKFLOW
    if not workflow.exists():
        return [f"Missing canonical workflow: {WORKFLOW}"]

    text = workflow.read_text(encoding="utf-8")
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"Canonical workflow is missing `{snippet}`")
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
        "Canonical CI workflow invariants are present; this structural check "
        "does not establish hosted-job success."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
