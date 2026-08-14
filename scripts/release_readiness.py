#!/usr/bin/env python3
"""New-user release readiness gate.

This is not a coverage threshold. It black-box exercises the exact surface a
brand-new user touches on their first day and fails the release if any pillar
is unmet:

  1. Proven installation      — the installed entry points actually run.
  2. Guided troubleshooting   — every failure carries an actionable fix.
  3. Full feature validation  — each command/journey behaves as documented.
  4. Tested recovery paths     — batch resume, corruption, and reset work.
  5. Documentation             — generated docs, links, guides, and command
                                 coverage are current and complete.

Run it against an *installed* package (ideally from a built wheel in a clean
environment) so it proves what a user gets, not what the working tree contains:

    python -m build
    python -m venv /tmp/fresh && /tmp/fresh/bin/pip install dist/*.whl
    /tmp/fresh/bin/python scripts/release_readiness.py

Exit code 0 means release-ready; 1 means at least one gate failed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# A run of token-shaped characters long enough to be an unmasked secret. The
# masking helper only ever reveals a 4-char prefix, so a match means a real leak.
FULL_TOKEN = re.compile(r"(?:sk|xai|gsk)-[A-Za-z0-9_-]{16,}")

ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, "-m", "pocarchitect"]

# Commands that must exist and be validated somewhere in this gate.
REQUIRED_COMMANDS = {
    "preflight",
    "setup",
    "config",
    "batch-status",
    "batch-reset",
}
SAFE_EXAMPLE_URL = "https://github.com/example/poc"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Pillar:
    key: str
    title: str
    checks: list[Check] = field(default_factory=list)

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.checks.append(Check(name, passed, detail))

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


def _clean_env() -> dict[str, str]:
    """Environment with provider keys and container hints removed.

    Guarantees deterministic results regardless of the runner's own secrets.
    """
    env = dict(os.environ)
    for key in ("XAI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "IN_DOCKER"):
        env.pop(key, None)
    return env


def run_cli(
    args: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke the installed CLI through its module entry point."""
    return subprocess.run(
        CLI + args,
        cwd=str(cwd),
        env=env or _clean_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def json_events(stdout: str) -> list[dict]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


# ── Pillar 1: Proven installation ────────────────────────────────────────────
def pillar_installation(work: Path) -> Pillar:
    p = Pillar("installation", "Proven installation")

    version = run_cli(["--version"], work)
    p.record(
        "`--version` runs and reports a version",
        version.returncode == 0 and "POCArchitect" in version.stdout,
        version.stdout.strip() or version.stderr.strip(),
    )

    help_result = run_cli(["--help"], work)
    p.record(
        "`--help` runs",
        help_result.returncode == 0 and "Usage" in help_result.stdout,
    )

    preflight = run_cli(["preflight", "--offline", "--format", "json"], work)
    events = json_events(preflight.stdout)
    passed = bool(events) and events[-1].get("message") == "Preflight passed."
    p.record(
        "`preflight --offline` passes in a clean install",
        preflight.returncode == 0 and passed,
        events[-1].get("message", "") if events else preflight.stderr.strip(),
    )

    # The console entry point (not just `-m`) must be importable/available.
    try:
        from importlib.metadata import entry_points

        scripts = entry_points(group="console_scripts")
        has_script = any(ep.name == "pocarchitect" for ep in scripts)
    except Exception as error:  # noqa: BLE001
        has_script = False
        p.record("`pocarchitect` console script registered", False, str(error))
    else:
        p.record("`pocarchitect` console script registered", has_script)

    return p


# ── Pillar 2: Guided troubleshooting ─────────────────────────────────────────
def pillar_troubleshooting(work: Path) -> Pillar:
    p = Pillar("troubleshooting", "Guided troubleshooting")

    # A failing preflight must attach a non-empty remediation to every failure.
    # `groq` is used because it has no key in a clean install or the dev tree,
    # so this failure is deterministic regardless of ambient credentials.
    result = run_cli(["preflight", "--provider", "groq", "--format", "json"], work)
    events = json_events(result.stdout)
    checks = events[-1].get("checks", []) if events else []
    failures = [c for c in checks if "FAIL" in c.get("status", "")]
    have_failure = bool(failures)
    all_have_fix = all(c.get("remediation", "").strip() for c in failures)
    p.record(
        "Failing preflight surfaces at least one failure",
        have_failure,
        f"{len(failures)} failing checks",
    )
    p.record(
        "Every failing preflight row carries a remediation",
        have_failure and all_have_fix,
        "; ".join(f"{c['check']} -> {c.get('remediation', '')[:40]}" for c in failures),
    )

    # Friendly, category-specific guidance for the common provider errors.
    from pocarchitect.cli import friendly_error_message

    cases = {
        "unauthorized 401": "credential",
        "429 rate limit": "rate limit",
        "model `x` does not exist": "model",
    }
    guidance_ok = True
    details = []
    for raw, expected in cases.items():
        message = friendly_error_message(Exception(raw)).lower()
        ok = expected in message
        guidance_ok = guidance_ok and ok
        details.append(f"{raw!r}->{'ok' if ok else 'MISSING'}")
    p.record(
        "Common provider errors map to specific guidance",
        guidance_ok,
        ", ".join(details),
    )

    # An invalid URL fails early with an actionable message (not a deep crash).
    bad = run_cli(["--url", "https://github.com/onlyowner", "--dry-run"], work)
    p.record(
        "Malformed GitHub URL is rejected early with guidance",
        bad.returncode == 2 and "Invalid PoC URL" in (bad.stdout + bad.stderr),
        bad.stdout.strip()[-120:],
    )

    # The novice guide ships a troubleshooting matrix.
    guide = (ROOT / "docs" / "NOVICE_USABILITY_GUIDE.md").read_text(encoding="utf-8")
    p.record(
        "Novice guide includes a troubleshooting matrix",
        "Troubleshooting Matrix" in guide and "Diagnose and Fix" in guide,
    )
    return p


# ── Pillar 3: Full feature validation ────────────────────────────────────────
def pillar_features(work: Path) -> Pillar:
    p = Pillar("features", "Full feature validation")

    # Every declared command must exist in the CLI metadata.
    from typer.main import get_command

    from pocarchitect.cli import app

    root = get_command(app)
    command_names = set(root.commands.keys())  # type: ignore[attr-defined]
    missing = REQUIRED_COMMANDS - command_names
    p.record(
        "All required commands are present",
        not missing,
        f"missing: {sorted(missing)}" if missing else "ok",
    )

    # config exposes effective settings as machine-readable data.
    config = run_cli(["--format", "json", "config"], work)
    config_event = next(
        (e for e in json_events(config.stdout) if e.get("event") == "config"), None
    )
    p.record(
        "`config` reports effective settings",
        config.returncode == 0
        and config_event is not None
        and isinstance(config_event.get("settings"), list),
    )
    # Keys must be masked, never printed in full.
    p.record(
        "`config` never prints a raw secret value",
        FULL_TOKEN.search(config.stdout) is None,
    )

    # Dry-run default is a compact summary; --full expands it. Both exit cleanly.
    summary = run_cli(
        ["--url", "octocat/Hello-World", "--no-ingest", "--dry-run", "--no-color"],
        work,
    )
    p.record(
        "`--dry-run` prints a summary and accepts owner/repo shorthand",
        summary.returncode == 0
        and "Dry-Run Summary" in summary.stdout
        and "octocat/Hello-World" in summary.stdout,
        summary.stdout.strip()[:80],
    )

    full = run_cli(
        [
            "--url",
            "octocat/Hello-World",
            "--no-ingest",
            "--dry-run",
            "--full",
            "--no-color",
        ],
        work,
    )
    p.record(
        "`--dry-run --full` prints the entire prompt",
        full.returncode == 0 and "Full Prompt" in full.stdout,
    )

    # JSON dry-run is a stable two-event stream ending in dry_run.
    js = run_cli(
        [
            "--url",
            "octocat/Hello-World",
            "--no-ingest",
            "--dry-run",
            "--format",
            "json",
            "--no-color",
        ],
        work,
    )
    events = json_events(js.stdout)
    stream_ok = [e.get("event") for e in events] == ["processing", "dry_run"]
    shorthand_ok = events and events[0].get("url") == (
        "https://github.com/octocat/Hello-World"
    )
    p.record(
        "JSON dry-run is a stable machine-readable stream",
        js.returncode == 0 and stream_ok and bool(shorthand_ok),
    )

    # --no-mitigations actually changes the assembled prompt.
    nomit = run_cli(
        [
            "--url",
            "octocat/Hello-World",
            "--no-ingest",
            "--no-mitigations",
            "--dry-run",
            "--format",
            "json",
            "--no-color",
        ],
        work,
    )
    nomit_events = json_events(nomit.stdout)
    prompt = nomit_events[-1].get("prompt", "") if nomit_events else ""
    p.record(
        "`--no-mitigations` is reflected in the prompt",
        "Include Mitigations: No" in prompt,
    )
    return p


# ── Pillar 4: Tested recovery paths ──────────────────────────────────────────
def _seed_ledger(path: Path, items: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": 2, "items": items}, indent=2), encoding="utf-8"
    )


def pillar_recovery(work: Path) -> Pillar:
    p = Pillar("recovery", "Tested recovery paths")

    ledger = work / "ledger.json"
    _seed_ledger(
        ledger,
        {
            "https://github.com/example/done": {"status": "success"},
            "https://github.com/example/fail": {"status": "failed"},
        },
    )

    status = run_cli(["batch-status", "--batch-state", str(ledger)], work)
    p.record(
        "`batch-status` summarizes a ledger",
        status.returncode == 0
        and "total=2" in status.stdout
        and "success=1" in status.stdout,
        status.stdout.strip()[-100:],
    )

    # Resume: a completed URL is skipped on the next run.
    batch_file = work / "urls.txt"
    batch_file.write_text(
        "https://github.com/example/done\nhttps://github.com/example/new\n",
        encoding="utf-8",
    )
    resume = run_cli(
        [
            "--batch",
            str(batch_file),
            "--no-ingest",
            "--dry-run",
            "--format",
            "json",
            "--no-color",
            "--batch-state",
            str(ledger),
        ],
        work,
    )
    resume_events = [e.get("event") for e in json_events(resume.stdout)]
    p.record(
        "Completed URLs are skipped on resume",
        "batch_skipped" in resume_events,
        ",".join(resume_events),
    )

    # Corruption is preserved, not silently discarded, and points to the fix.
    corrupt = work / "corrupt.json"
    corrupt.write_text("{not valid json", encoding="utf-8")
    corrupt_status = run_cli(["batch-status", "--batch-state", str(corrupt)], work)
    p.record(
        "Corrupt ledger fails safely and names the recovery command",
        corrupt_status.returncode == 2
        and "batch-reset" in (corrupt_status.stdout + corrupt_status.stderr),
    )

    # Reset is recoverable: it backs the ledger up rather than deleting it.
    reset = run_cli(["batch-reset", "--batch-state", str(corrupt), "--yes"], work)
    backups = list(work.glob("corrupt.reset-*.json.bak"))
    p.record(
        "`batch-reset` retains a recoverable backup",
        reset.returncode == 0 and bool(backups) and not corrupt.exists(),
    )

    # Missing ledger yields guidance, not a stack trace.
    empty = run_cli(["batch-status", "--batch-state", str(work / "none.json")], work)
    p.record(
        "Absent ledger yields a friendly message",
        empty.returncode == 0,  # explicit missing path -> empty state summary
    )
    return p


# ── Pillar 5: Documentation ──────────────────────────────────────────────────
def _run_script(rel: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / rel), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def pillar_documentation() -> Pillar:
    p = Pillar("documentation", "Documentation")

    gen = _run_script("scripts/generate_docs.py", "--check")
    p.record(
        "Generated docs are current (no drift)",
        gen.returncode == 0,
        gen.stdout.strip()[-100:],
    )

    links = _run_script("scripts/validate_documentation_links.py")
    p.record("Local documentation links resolve", links.returncode == 0)

    guides = _run_script("scripts/validate_novice_guides.py")
    p.record("Novice guides pass their validator", guides.returncode == 0)

    # Every CLI command is documented in the generated reference.
    reference = (ROOT / "docs" / "cli-reference.md").read_text(encoding="utf-8")
    undocumented = sorted(c for c in REQUIRED_COMMANDS if f"`{c}`" not in reference)
    p.record(
        "Every command appears in the CLI reference",
        not undocumented,
        f"undocumented: {undocumented}" if undocumented else "ok",
    )

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    p.record(
        "README documents the safe first run and setup wizard",
        SAFE_EXAMPLE_URL in readme and "pocarchitect setup" in readme,
    )
    return p


def collect(work: Path) -> list[Pillar]:
    return [
        pillar_installation(work),
        pillar_troubleshooting(work),
        pillar_features(work),
        pillar_recovery(work),
        pillar_documentation(),
    ]


def render_text(pillars: list[Pillar]) -> str:
    lines = ["POCArchitect - New-User Release Readiness", "=" * 44, ""]
    for pillar in pillars:
        mark = "PASS" if pillar.passed else "FAIL"
        lines.append(f"[{mark}] {pillar.title}")
        for check in pillar.checks:
            symbol = "  ok " if check.passed else "  XX "
            suffix = f"  ({check.detail})" if check.detail and not check.passed else ""
            lines.append(f"{symbol}{check.name}{suffix}")
        lines.append("")
    overall = all(p.passed for p in pillars)
    lines.append("RESULT: " + ("READY FOR RELEASE" if overall else "NOT READY"))
    return "\n".join(lines)


def render_json(pillars: list[Pillar]) -> str:
    return json.dumps(
        {
            "ready": all(p.passed for p in pillars),
            "pillars": [
                {
                    "key": pillar.key,
                    "title": pillar.title,
                    "passed": pillar.passed,
                    "checks": [
                        {"name": c.name, "passed": c.passed, "detail": c.detail}
                        for c in pillar.checks
                    ],
                }
                for pillar in pillars
            ],
        },
        indent=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        pillars = collect(Path(tmp))

    output = render_json(pillars) if args.format == "json" else render_text(pillars)
    print(output)
    return 0 if all(p.passed for p in pillars) else 1


if __name__ == "__main__":
    raise SystemExit(main())
