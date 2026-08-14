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
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterator

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

# Values the hermetic mock provider advertises so a run can prove that the
# operator's --model/--temperature choices actually reach the provider call.
MOCK_MODEL = "mock-provider-model-x7"
MOCK_TEMPERATURE = 0.73
MOCK_MARKER = "POCARCHITECT_MOCK_REPORT_MARKER_7f3a9d"

# Every long option a new user can pass must be *functionally* exercised by this
# gate (covered) or explicitly, and narrowly, waived with a stated reason. The
# coverage check in Pillar 3 reads the live CLI metadata and fails if a new
# option ships without landing in one of these sets — that is what makes
# "all options, no exceptions" enforceable rather than aspirational.
COVERED_OPTIONS: dict[str, str] = {
    "--version": "`--version` is run and asserted in Pillar 1.",
    "--show-completion": "Shell completion is emitted and asserted in Pillar 1.",
    "--offline": "`preflight --offline` is asserted in Pillar 1.",
    "--url": "Single-URL journeys drive Pillars 2 and 3.",
    "--batch": "Batch resume is asserted in Pillar 4.",
    "--batch-state": "Ledger inspection/reset is asserted in Pillar 4.",
    "--provider": "Selected provider is exercised end-to-end via the mock in Pillar 3.",
    "--model": "Model reaches the provider call (mock captures it) in Pillar 3.",
    "--temperature": "Temperature reaches the provider call (mock captures it) in Pillar 3.",
    "--base-url": "Local endpoint routing is proven against the mock in Pillar 3.",
    "--output-dir": "Report is written to the chosen directory in Pillar 3.",
    "--risk-level": "Reflected in the assembled prompt in Pillar 3.",
    "--target-os": "Reflected in the assembled prompt in Pillar 3.",
    "--include-mitigations": "Default 'Yes' is asserted in the prompt in Pillar 3.",
    "--no-mitigations": "Toggled 'No' is asserted in the prompt in Pillar 3.",
    "--no-ingest": "Grounding-skip path is used throughout Pillars 2-4.",
    "--dry-run": "Summary/JSON dry-run is asserted in Pillar 3.",
    "--full": "`--dry-run --full` prints the whole prompt in Pillar 3.",
    "--open": "Report-open path is exercised end-to-end in Pillar 3.",
    "--verbose": "Verbose model selection is asserted in Pillar 3.",
    "--yes": "Non-interactive confirmation is used in Pillars 3 and 4.",
    "--format": "Text and JSON modes are asserted throughout.",
    "--no-color": "Color-free output is used throughout.",
}
WAIVED_OPTIONS: dict[str, str] = {
    "--install-completion": (
        "Writes to the user's shell profile (a side effect a gate must not cause); "
        "its read-only sibling --show-completion is exercised instead."
    ),
}


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
    """Invoke the installed CLI through its module entry point.

    stdin is an empty pipe (never a TTY) so interactive prompts abort
    deterministically as "non-interactive" on every platform — notably Windows,
    where a redirected NUL device still reports ``isatty() == True``.
    """
    return subprocess.run(
        CLI + args,
        cwd=str(cwd),
        env=env or _clean_env(),
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


# ── Hermetic mock provider ───────────────────────────────────────────────────
class _MockProviderHandler(BaseHTTPRequestHandler):
    """A minimal OpenAI-compatible endpoint that records the requests it gets.

    It answers the two calls a real ``--provider local`` run makes: the
    ``GET /models`` reachability probe that preflight issues, and the
    ``POST /chat/completions`` the analysis performs. Capturing the POST body
    lets the gate prove that ``--model`` and ``--temperature`` reached the wire.
    """

    requests: list[dict] = []

    def log_message(self, *args: object) -> None:  # noqa: D401 — silence logging
        pass

    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 — http.server API
        if self.path.endswith("/models"):
            self._send(200, {"object": "list", "data": [{"id": MOCK_MODEL}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 — http.server API
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            payload = {}
        type(self).requests.append(payload)
        self._send(
            200,
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 0,
                "model": payload.get("model", MOCK_MODEL),
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": f"# Mock Analysis\n\n{MOCK_MARKER}\n",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )


@contextmanager
def mock_provider() -> Iterator[tuple[str, list[dict]]]:
    """Run the mock endpoint on an ephemeral port for the duration of a block."""
    _MockProviderHandler.requests = []
    server = HTTPServer(("127.0.0.1", 0), _MockProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/v1"
        yield base_url, _MockProviderHandler.requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def all_long_options() -> set[str]:
    """Every ``--long`` option the CLI accepts, across the root and subcommands."""
    from typer.main import get_command

    from pocarchitect.cli import app

    root = get_command(app)
    options: set[str] = set()

    def collect(command) -> None:  # noqa: ANN001 — click object
        for param in command.params:
            names = list(getattr(param, "opts", [])) + list(
                getattr(param, "secondary_opts", [])
            )
            options.update(name for name in names if name.startswith("--"))

    collect(root)
    for command in root.commands.values():  # type: ignore[attr-defined]
        collect(command)
    return options


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

    # Shell completion ships and is emitted without touching the user's profile.
    completion = run_cli(["--show-completion"], work)
    p.record(
        "`--show-completion` emits a completion script",
        completion.returncode == 0 and bool(completion.stdout.strip()),
        completion.stderr.strip()[:80],
    )

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

    # The interactive wizard refuses to run non-interactively and points the
    # user at the scriptable alternative instead of hanging or aborting raw.
    setup = run_cli(["--format", "json", "setup"], work)
    setup_event = next(
        (e for e in json_events(setup.stdout) if e.get("event") == "error"), None
    )
    setup_msg = (setup_event or {}).get("message", "")
    p.record(
        "`setup` refuses non-interactive use with actionable guidance",
        setup.returncode == 2
        and "interactive" in setup_msg
        and "preflight" in setup_msg,
        setup_msg[:80],
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

    # "No exceptions" made enforceable: every long option the CLI exposes must be
    # functionally covered by this gate or explicitly waived. A newly shipped
    # option that is neither trips this check until it is validated.
    options = all_long_options()
    accounted = set(COVERED_OPTIONS) | set(WAIVED_OPTIONS)
    uncovered = sorted(options - accounted)
    stale = sorted(accounted - options)
    p.record(
        "Every CLI option is covered by the gate (no exceptions)",
        not uncovered and not stale,
        (f"uncovered: {uncovered}; " if uncovered else "")
        + (f"stale entries: {stale}" if stale else "")
        or f"{len(options)} options accounted for",
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

    # --risk-level, --target-os, and the default --include-mitigations all reach
    # the operator-preferences block the provider is instructed to honor.
    prefs = run_cli(
        [
            "--url",
            "octocat/Hello-World",
            "--no-ingest",
            "--dry-run",
            "--risk-level",
            "Critical",
            "--target-os",
            "Windows Server 2022",
            "--format",
            "json",
            "--no-color",
        ],
        work,
    )
    prefs_prompt = (json_events(prefs.stdout)[-1:] or [{}])[0].get("prompt", "")
    p.record(
        "`--risk-level`/`--target-os`/`--include-mitigations` shape the prompt",
        "Risk Level: Critical" in prefs_prompt
        and "Target OS / Environment: Windows Server 2022" in prefs_prompt
        and "Include Mitigations: Yes" in prefs_prompt,
    )

    # --verbose surfaces the default-model selection a novice would want to see.
    verbose = run_cli(
        [
            "--url",
            "octocat/Hello-World",
            "--no-ingest",
            "--dry-run",
            "--verbose",
            "--format",
            "json",
            "--no-color",
        ],
        work,
    )
    p.record(
        "`--verbose` reports which model was selected",
        any(e.get("event") == "model_selected" for e in json_events(verbose.stdout)),
    )

    # A real (but hermetic) provider run: --provider local + --base-url routes to
    # the mock, --model/--temperature reach the wire, --output-dir receives the
    # report, and --open exercises the viewer-launch path. This closes the old
    # "no automated live run" boundary for everything except a paid credential.
    out_dir = work / "mock-out"
    open_supported = sys.platform != "win32"  # avoid launching a GUI app locally
    with mock_provider() as (base_url, captured):
        pre = run_cli(
            [
                "preflight",
                "--provider",
                "local",
                "--base-url",
                base_url,
                "--format",
                "json",
            ],
            work,
        )
        pre_events = json_events(pre.stdout)
        p.record(
            "`preflight --base-url` validates a reachable local endpoint",
            pre.returncode == 0
            and bool(pre_events)
            and pre_events[-1].get("message") == "Preflight passed.",
            pre_events[-1].get("message", "") if pre_events else pre.stderr.strip(),
        )

        run_args = [
            "--url",
            "octocat/Hello-World",
            "--no-ingest",
            "--provider",
            "local",
            "--base-url",
            base_url,
            "--model",
            MOCK_MODEL,
            "--temperature",
            str(MOCK_TEMPERATURE),
            "--output-dir",
            str(out_dir),
            "--format",
            "json",
            "--yes",
            "--no-color",
        ]
        if open_supported:
            run_args.append("--open")
        e2e = run_cli(run_args, work)

    e2e_events = json_events(e2e.stdout)
    e2e_names = [e.get("event") for e in e2e_events]
    saved = next((e for e in e2e_events if e.get("event") == "report_saved"), None)
    report_files = list(out_dir.glob("*.md")) if out_dir.exists() else []
    report_text = report_files[0].read_text(encoding="utf-8") if report_files else ""

    p.record(
        "`--provider local`/`--base-url` reach the provider and return a report",
        e2e.returncode == 0 and saved is not None and MOCK_MARKER in report_text,
        ",".join(n for n in e2e_names if n),
    )
    p.record(
        "`--model`/`--temperature` reach the provider call unchanged",
        bool(captured)
        and captured[-1].get("model") == MOCK_MODEL
        and abs(float(captured[-1].get("temperature", -1)) - MOCK_TEMPERATURE) < 1e-9,
        json.dumps(captured[-1]) if captured else "no request captured",
    )
    p.record(
        "`--output-dir` receives the report with faithful metadata",
        bool(report_files)
        and f"model: {json.dumps(MOCK_MODEL)}" in report_text
        and 'provider: "local"' in report_text,
        str(report_files[0]) if report_files else "no report written",
    )
    p.record(
        "`--open` drives the report-viewer path",
        (not open_supported)  # exercised at the Linux CI enforcement point
        or ("report_opened" in e2e_names or "report_open_failed" in e2e_names),
        (
            "skipped on win32 (GUI side effect); enforced in CI"
            if not open_supported
            else ",".join(n for n in e2e_names if n)
        ),
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
