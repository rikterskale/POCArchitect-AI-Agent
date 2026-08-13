# Contributing to POCArchitect

Thanks for your interest in improving POCArchitect. This guide describes how to
set up a development environment and run the same checks that CI enforces, so a
pull request passes on the first try.

Only analyze or reference repositories you are authorized to inspect. Never
commit a `.env` file or place a provider key on a command line, in a test
fixture, or in an issue.

## Prerequisites

- Python 3.10 or newer. CI runs the test suite on Python 3.10, 3.11, 3.12, and 3.13.
- Git.

## Development setup

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements-dev.txt
```

`requirements-dev.txt` pins the developer toolchain, including `ruff==0.15.9`.
Use that exact Ruff version locally; a different version can format code in a
way CI then rejects.

## Local checks (mirror CI exactly)

CI runs three gating stages — `quality`, `test`, `security` — plus a Docker
build. Run their commands locally before opening a pull request. Every command
runs from the repository root.

Quality:

```bash
ruff check .
ruff format --check .
black --check --diff .
mypy pocarchitect tests
python scripts/generate_docs.py --check
python scripts/validate_novice_guides.py
python scripts/validate_documentation_links.py
```

Tests (with coverage):

```bash
pytest --cov=pocarchitect --cov-report=xml
```

Dependency vulnerability scan:

```bash
pip-audit
```

A convenience script, `verify.sh`, runs an install plus dry-run smoke test on
Bash, WSL, Git Bash, Linux, or macOS. `test-full.sh` makes real provider calls
and consumes credits — review it before running.

## Generated documentation

`docs/cli-reference.md` and `docs/configuration-reference.md` are generated from
the CLI metadata in `pocarchitect/cli.py`. If you change a command, option,
default, or help string, regenerate them:

```bash
python scripts/generate_docs.py
```

CI runs `python scripts/generate_docs.py --check` and fails if the checked-in
reference is out of date, so commit the regenerated files with your change. Do
not hand-edit the generated references.

## Change and pull request workflow

1. Create a branch from `main`.
2. Make your change, adding or updating tests under `tests/`.
3. Run every local check above until each passes.
4. If you changed CLI metadata, regenerate the docs.
5. Open a pull request against `main` describing the change and its rationale.
   CI must pass before review.

## Reporting problems

Open an issue at
<https://github.com/rikterskale/POCArchitect-AI-Agent/issues>. Include your
operating system, Python version, the provider name (never the key), the
command used with any secrets removed, the exit code, and the smallest relevant
error output. A helpful baseline to attach:

```bash
python -m pocarchitect --version
python -m pocarchitect preflight --offline --format json --no-color
```
