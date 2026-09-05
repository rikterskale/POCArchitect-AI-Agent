import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from pocarchitect import cli

RUNNER = CliRunner()


def test_windows_help_uses_plain_renderer_for_redirected_output():
    result = subprocess.run(
        [sys.executable, "-m", "pocarchitect", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: python -m pocarchitect" in result.stdout
    expected_markup = None if sys.platform.startswith("win") else "rich"
    assert cli.app.rich_markup_mode == expected_markup


def test_normalize_github_repo_url_supports_common_variants():
    repo_name, clone_url = cli.normalize_github_repo_url(
        "https://github.com/octocat/Hello-World"
    )
    assert repo_name == "octocat/Hello-World"
    assert clone_url == "https://github.com/octocat/Hello-World.git"

    repo_name, clone_url = cli.normalize_github_repo_url(
        "https://www.github.com/octocat/Hello-World/"
    )
    assert repo_name == "octocat/Hello-World"
    assert clone_url == "https://github.com/octocat/Hello-World.git"

    repo_name, clone_url = cli.normalize_github_repo_url(
        "https://github.com/octocat/Hello-World.git"
    )
    assert repo_name == "octocat/Hello-World"
    assert clone_url == "https://github.com/octocat/Hello-World.git"

    repo_name, clone_url = cli.normalize_github_repo_url(
        "https://github.com/octocat/Hello-World.GIT"
    )
    assert repo_name == "octocat/Hello-World"
    assert clone_url == "https://github.com/octocat/Hello-World.git"

    repo_name, clone_url = cli.normalize_github_repo_url(
        "https://github.com/octocat/Hello-World/tree/main"
    )
    assert repo_name == "octocat/Hello-World"
    assert clone_url == "https://github.com/octocat/Hello-World.git"


def test_normalize_github_repo_url_rejects_non_github():
    with pytest.raises(ValueError):
        cli.normalize_github_repo_url("https://gitlab.com/octocat/Hello-World")


def test_process_batch_file_reports_success_failure_and_failed_urls(
    tmp_path, monkeypatch
):
    batch_file = tmp_path / "batch.txt"
    batch_file.write_text(
        "https://github.com/example/good\nhttps://github.com/example/bad\n",
        encoding="utf-8",
    )

    def fake_process_single_url(url, **kwargs):
        if url.endswith("/bad"):
            raise RuntimeError("boom")

    output = io.StringIO()
    monkeypatch.setattr(cli, "process_single_url", fake_process_single_url)
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=output, force_terminal=False, color_system=None),
    )

    with pytest.raises(typer.Exit) as error:
        cli.process_batch_file(
            batch_path=batch_file,
            provider="openai",
            api_key=None,
            model="gpt-4o",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path / "reports",
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=True,
            dry_run=False,
            verbose=False,
        )

    assert error.value.exit_code == 1
    text = output.getvalue()
    assert "total=2 processed=2 success=1 failed=1 skipped=0" in text
    assert "https://github.com/example/bad" in text


def test_process_batch_file_dry_run_previews_every_eligible_url(tmp_path, monkeypatch):
    batch_file = tmp_path / "batch.txt"
    batch_file.write_text(
        "https://github.com/example/one\nhttps://github.com/example/two\n",
        encoding="utf-8",
    )

    def fake_process_single_url(url, **kwargs):
        raise typer.Exit(0)

    output = io.StringIO()
    monkeypatch.setattr(cli, "process_single_url", fake_process_single_url)
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=output, force_terminal=False, color_system=None),
    )

    cli.process_batch_file(
        batch_path=batch_file,
        provider="openai",
        api_key=None,
        model="gpt-4o",
        temperature=0.2,
        base_url=None,
        output_dir=tmp_path / "reports",
        risk_level="High",
        target_os="Linux",
        include_mitigations=True,
        no_ingest=True,
        dry_run=True,
        verbose=False,
    )

    text = output.getvalue()
    assert "total=2 processed=2 success=2 failed=0 skipped=0" in text
    assert "processed only the first URL" not in text


def test_cli_rejects_url_and_batch_together(tmp_path):
    batch_file = tmp_path / "batch.txt"
    batch_file.write_text("https://github.com/example/repo\n", encoding="utf-8")

    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://github.com/example/repo",
            "--batch",
            str(batch_file),
            "--dry-run",
        ],
    )

    assert result.exit_code == 2
    assert "Provide either --url or --batch, not both" in result.stdout


def test_doctor_offline_runs_installation_diagnosis(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = RUNNER.invoke(
        cli.app, ["--format", "json", "--no-color", "doctor", "--offline"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["event"] == "preflight"
    assert payload["message"] == "Preflight passed."


def test_demo_creates_report_without_credentials_or_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = RUNNER.invoke(cli.app, ["--format", "json", "--no-color", "demo"])

    assert result.exit_code == 0, result.stdout
    report = tmp_path / "reports" / "demo"
    reports = list(report.glob("*.md"))
    assert reports
    assert "credential-free report" in reports[0].read_text(encoding="utf-8")


def test_demo_does_not_require_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    original_preflight = cli.run_preflight

    def capture_preflight(**kwargs):
        calls.append(kwargs)
        return original_preflight(**kwargs)

    monkeypatch.setattr(cli, "run_preflight", capture_preflight)

    result = RUNNER.invoke(cli.app, ["--format", "json", "--no-color", "demo"])

    assert result.exit_code == 0, result.stdout
    assert calls and calls[0]["require_git"] is False
    assert calls[0]["offline"] is True
    assert calls[0]["require_api_key"] is False
    assert calls[0].get("base_url") is None


def test_cost_limit_aborts_before_provider_call(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_prompt", lambda: "system prompt")
    called = []
    monkeypatch.setattr(cli, "get_llm_response", lambda **kwargs: called.append(kwargs))

    with pytest.raises(typer.Exit) as error:
        cli.process_single_url(
            url="https://example.com/poc",
            provider="openai",
            api_key=None,
            model="gpt-4o",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path,
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=True,
            max_estimated_cost=0.0,
        )

    assert error.value.exit_code == 2
    assert called == []


def test_ingestion_failure_exits_before_provider_call(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_prompt", lambda: "system prompt")
    monkeypatch.setattr(
        cli,
        "build_grounding_context",
        lambda *args, **kwargs: cli.GroundingResult(
            "WARNING: Ingestion failed.", "url-only-ingestion-failed"
        ),
    )
    monkeypatch.setattr(
        cli,
        "get_llm_response",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("provider must not be called")
        ),
    )
    events = []

    with cli.capture_events(events.append), pytest.raises(typer.Exit) as error:
        cli.process_single_url(
            url="https://github.com/example/missing",
            provider="openai",
            api_key="unused",
            model="gpt-4o",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path,
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=False,
        )

    assert error.value.exit_code == 2
    assert any(
        event["event"] == "error"
        and "Source ingestion failed; no provider call was made" in event["message"]
        for event in events
    )


def test_models_command_reports_defaults():
    result = RUNNER.invoke(cli.app, ["--format", "json", "models"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["event"] == "models"
    assert any(row["provider"] == "local" for row in payload["models"])


def test_process_batch_file_continues_after_non_dry_typer_exit(tmp_path, monkeypatch):
    batch_file = tmp_path / "batch.txt"
    batch_file.write_text(
        "https://github.com/example/exit\nhttps://github.com/example/good\n",
        encoding="utf-8",
    )

    def fake_process_single_url(url, **kwargs):
        if url.endswith("/exit"):
            raise typer.Exit(1)

    output = io.StringIO()
    monkeypatch.setattr(cli, "process_single_url", fake_process_single_url)
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=output, force_terminal=False, color_system=None),
    )

    with pytest.raises(typer.Exit) as error:
        cli.process_batch_file(
            batch_path=batch_file,
            provider="openai",
            api_key=None,
            model="gpt-4o",
            temperature=0.2,
            base_url=None,
            output_dir=tmp_path / "reports",
            risk_level="High",
            target_os="Linux",
            include_mitigations=True,
            no_ingest=True,
            dry_run=False,
            verbose=False,
        )

    assert error.value.exit_code == 1
    text = output.getvalue()
    assert "total=2 processed=2 success=1 failed=1 skipped=0" in text
    assert "https://github.com/example/exit" in text


def test_build_grounding_context_uses_non_interactive_timed_git_clone(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    grounding = cli.build_grounding_context("https://github.com/octocat/Hello-World")

    assert "Repository: octocat/Hello-World" in grounding.content
    assert grounding.ingestion == "github-shallow-clone"
    assert calls, "Expected git clone subprocess call"
    cmd, kwargs = calls[0]
    assert cmd[:4] == ["git", "clone", "--depth", "1"]
    assert kwargs["timeout"] == 90
    assert kwargs["check"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
    assert kwargs["env"]["PATH"] == os.environ["PATH"]


def test_grounding_fixture_exercises_selection_and_content(monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "grounding-repo"

    def fake_run(cmd, **kwargs):
        destination = Path(cmd[-1])
        shutil.copytree(
            fixture, destination, ignore=shutil.ignore_patterns("__pycache__")
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.build_grounding_context("https://github.com/example/fixture")

    assert result.ingestion == "github-shallow-clone"
    assert result.selected_files == 2
    assert "POCARCHITECT_GROUNDING_FIXTURE" in result.content


def test_save_report_contains_safe_metadata(tmp_path, monkeypatch):
    output = io.StringIO()
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=output, force_terminal=False, color_system=None),
    )

    report = cli.save_report(
        "# Report\n\nresult",
        "https://github.com/example/repo",
        tmp_path,
        "local",
        "test-model",
        cli.GroundingResult(
            "PoC URL: https://github.com/example/repo\n"
            "[Grounding disabled by --no-ingest]",
            "disabled",
        ),
    )

    text = report.read_text(encoding="utf-8")
    assert 'source_url: "https://github.com/example/repo"' in text
    assert 'provider: "local"' in text
    assert "content_sha256:" in text
    assert 'ingestion: "disabled"' in text
    assert "grounding_files_selected: 0" in text
    assert "test-model" in text
    if cli.os.name != "nt":
        assert cli.stat.S_IMODE(report.stat().st_mode) == 0o600
        assert cli.stat.S_IMODE((tmp_path / "history.json").stat().st_mode) == 0o600


def test_grounding_records_non_github_and_clone_failure_outcomes(monkeypatch):
    non_github = cli.build_grounding_context("https://example.com/advisory")

    def fail_clone(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(cli.subprocess, "run", fail_clone)
    failed_clone = cli.build_grounding_context("https://github.com/example/missing")

    assert non_github.ingestion == "url-only-non-github"
    assert "Non-GitHub URL" in non_github.content
    assert failed_clone.ingestion == "url-only-ingestion-failed"
    assert "WARNING: Ingestion failed" in failed_clone.content


def test_sensitive_input_detection_does_not_return_secret():
    secret = "OPENAI_API_KEY=sk-test-1234567890abcdef"
    categories = cli.detect_sensitive_input(secret)
    assert categories
    assert all("sk-test" not in category for category in categories)


def test_redact_sensitive_input_removes_values_before_transfer():
    source = "OPENAI_API_KEY=sk-test-1234567890abcdef\nkeep this context"

    redacted, categories, count = cli.redact_sensitive_input(source)

    assert categories == ["key/token assignment", "provider-token format"]
    assert count >= 1
    assert "sk-test-1234567890abcdef" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_sensitive_input_covers_common_cloud_and_bearer_tokens():
    source = "ghp_12345678901234567890 AKIA1234567890ABCDEF Bearer abcdefghijklmnop"
    redacted, categories, count = cli.redact_sensitive_input(source)
    assert count >= 2
    assert categories
    assert "ghp_12345678901234567890" not in redacted
    assert "AKIA1234567890ABCDEF" not in redacted
    assert "Bearer abcdefghijklmnop" not in redacted


def test_save_report_uses_unique_collision_safe_names(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "output_format", "json")
    first = cli.save_report(
        "# first",
        "https://github.com/example/poc",
        tmp_path,
        "local",
        "demo",
        cli.GroundingResult("", "disabled"),
    )
    second = cli.save_report(
        "# second",
        "https://github.com/example/poc",
        tmp_path,
        "local",
        "demo",
        cli.GroundingResult("", "disabled"),
    )
    assert first != second
    assert first.exists() and second.exists()


def test_json_dry_run_is_machine_readable_and_no_color():
    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://github.com/example/repo",
            "--no-ingest",
            "--dry-run",
            "--format",
            "json",
            "--no-color",
        ],
    )

    assert result.exit_code == 0
    events = [json.loads(line) for line in result.stdout.splitlines() if line]
    assert [event["event"] for event in events] == ["processing", "dry_run"]
    assert "\x1b" not in result.stdout
    assert events[-1]["prompt"].startswith("--- SYSTEM PROMPT ---")


def test_batch_status_reports_atomic_ledger_summary(tmp_path):
    state_path = tmp_path / "batch_progress.json"
    cli.write_state(
        state_path,
        {
            "version": 2,
            "items": {
                "https://github.com/example/ok": {"status": "success"},
                "https://github.com/example/fail": {"status": "failed"},
            },
        },
    )

    result = RUNNER.invoke(
        cli.app,
        [
            "--format",
            "json",
            "--no-color",
            "batch-status",
            "--batch-state",
            str(state_path),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["event"] == "batch_status"
    assert payload["total"] == 2
    assert payload["success"] == 1
    assert payload["failed"] == 1


def test_batch_reset_supports_global_json_output(tmp_path):
    state_path = tmp_path / "batch_progress.json"
    cli.write_state(state_path, {"version": 2, "items": {}})

    result = RUNNER.invoke(
        cli.app,
        [
            "--format",
            "json",
            "--no-color",
            "batch-reset",
            "--batch-state",
            str(state_path),
            "--yes",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["event"] == "batch_reset"
    assert payload["backup_path"].endswith(".json.bak")


def test_batch_command_exits_nonzero_after_dry_run_item_failure(tmp_path, monkeypatch):
    batch_file = tmp_path / "batch.txt"
    batch_file.write_text("https://example.com/one\nhttps://example.com/two\n")

    def fake_process(url, **kwargs):
        raise typer.Exit(1 if url.endswith("one") else 0)

    monkeypatch.setattr(cli, "process_single_url", fake_process)

    result = RUNNER.invoke(
        cli.app,
        ["--batch", str(batch_file), "--no-ingest", "--dry-run"],
    )

    assert result.exit_code == 1
    assert "processed=2 success=1 failed=1 skipped=0" in result.stdout


def test_main_preflights_the_resolved_output_directory(tmp_path, monkeypatch):
    output_dir = tmp_path / "custom-reports"
    calls = []
    monkeypatch.setattr(cli, "run_preflight", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(cli, "process_single_url", lambda **kwargs: None)

    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://example.com/advisory",
            "--no-ingest",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert calls[0]["output_dir"] == output_dir


def test_dry_run_bypasses_automatic_preflight(monkeypatch):
    monkeypatch.setattr(
        cli,
        "run_preflight",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("dry-run must bypass automatic preflight")
        ),
    )

    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://example.com/advisory",
            "--no-ingest",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0


def test_expand_url_shorthand_expands_owner_repo():
    assert (
        cli.expand_url_shorthand("octocat/Hello-World")
        == "https://github.com/octocat/Hello-World"
    )
    # Full URLs and non-shorthand values pass through unchanged.
    assert (
        cli.expand_url_shorthand("https://github.com/octocat/Hello-World")
        == "https://github.com/octocat/Hello-World"
    )
    assert (
        cli.expand_url_shorthand("https://example.com/a/b") == "https://example.com/a/b"
    )
    # A hostname-looking first segment is not shorthand.
    assert cli.expand_url_shorthand("example.com/repo") == "example.com/repo"


def test_validate_poc_url_rejects_malformed_github_url():
    import pytest

    with pytest.raises(ValueError):
        cli.validate_poc_url("https://github.com/onlyowner", no_ingest=False)
    # With --no-ingest, no early clone-shaped validation is applied.
    assert (
        cli.validate_poc_url("https://github.com/onlyowner", no_ingest=True)
        == "https://github.com/onlyowner"
    )


def test_estimate_cost_usd_known_and_unknown_models():
    cost = cli.estimate_cost_usd("gpt-4o", 1_000_000)
    assert cost == 2.50
    assert cli.estimate_cost_usd("grok-4.6", 1_000_000) == 2.00
    assert cli.estimate_cost_usd("openai/gpt-oss-120b", 1_000_000) == 0.15
    assert cli.estimate_cost_usd("no-such-model", 1_000_000) is None


def test_every_cloud_default_is_known_and_has_a_cost_estimate():
    for provider in ("xai", "openai", "groq"):
        model = cli.DEFAULT_MODELS[provider]
        assert model in cli.KNOWN_MODELS[provider]
        assert cli.estimate_cost_usd(model, 1_000_000) is not None


def test_save_report_emits_absolute_path_and_digest(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(cli, "output_format", "json")
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=io.StringIO(), force_terminal=False, color_system=None),
    )
    real_emit = cli.emit

    def capture(event, message, **details):
        events.append((event, details))
        real_emit(event, message, **details)

    monkeypatch.setattr(cli, "emit", capture)

    cli.save_report(
        "# Title\n\nFirst meaningful line\nSecond line",
        "https://github.com/example/repo",
        tmp_path,
        "local",
        "test-model",
        cli.GroundingResult("Grounding disabled", "disabled"),
    )

    names = [event for event, _ in events]
    assert "report_saved" in names
    assert "report_digest" in names
    saved = dict(events[[e for e, _ in events].index("report_saved")][1])
    assert "absolute_path" in saved


def test_resolve_batch_state_path_prefers_existing(tmp_path):
    # Non-default explicit path returns as-is only when it exists.
    missing = tmp_path / "nope.json"
    assert cli.resolve_batch_state_path(missing) is None
    missing.write_text("{}", encoding="utf-8")
    assert cli.resolve_batch_state_path(missing) == missing


def test_batch_status_reports_no_batch_when_ledger_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = RUNNER.invoke(cli.app, ["batch-status"])
    assert result.exit_code == 0
    assert "No batch has been run yet" in result.stdout


def test_config_command_masks_keys(tmp_path, monkeypatch):
    for key in ("XAI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=sk-secret-value-1234\n", encoding="utf-8"
    )

    result = RUNNER.invoke(cli.app, ["--format", "json", "config"])
    assert result.exit_code == 0
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    config_event = next(e for e in events if e["event"] == "config")
    settings = {row["setting"]: row for row in config_event["settings"]}
    assert "sk-secret-value-1234" not in result.stdout
    assert settings["OPENAI_API_KEY"]["value"].startswith("set (")


def test_no_mitigations_flag_is_reflected_in_prompt():
    result = RUNNER.invoke(
        cli.app,
        [
            "--url",
            "https://github.com/example/repo",
            "--no-ingest",
            "--no-mitigations",
            "--dry-run",
            "--format",
            "json",
            "--no-color",
        ],
    )
    assert result.exit_code == 0
    events = [json.loads(line) for line in result.stdout.splitlines() if line]
    prompt = events[-1]["prompt"]
    assert "Include Mitigations: No" in prompt


def test_get_llm_response_fails_fast_on_unknown_model(monkeypatch):
    calls = {"n": 0}

    class _Completions:
        def create(self, **_kwargs):
            calls["n"] += 1
            raise Exception("Error code: 404 - model `bogus` does not exist")

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    monkeypatch.setattr(cli, "OpenAI", lambda **_kwargs: _Client())
    monkeypatch.setattr(
        cli,
        "console",
        Console(file=io.StringIO(), force_terminal=False, color_system=None),
    )

    import pytest

    with pytest.raises(cli.FatalProviderError):
        cli.get_llm_response("openai", "sk-x", "bogus", 0.2, None, "sys", "user")
    # No retry storm: the create call happened exactly once.
    assert calls["n"] == 1


def test_corrupt_batch_state_is_preserved_until_explicit_reset(tmp_path):
    state_path = tmp_path / "batch_progress.json"
    state_path.write_text("{not valid json", encoding="utf-8")

    status = RUNNER.invoke(cli.app, ["batch-status", "--batch-state", str(state_path)])
    reset = RUNNER.invoke(
        cli.app, ["batch-reset", "--batch-state", str(state_path), "--yes"]
    )

    assert status.exit_code == 2
    assert "batch-reset" in status.stdout
    assert reset.exit_code == 0
    assert not state_path.exists()
    assert list(tmp_path.glob("batch_progress.reset-*.json.bak"))


def test_main_forwards_batch_feature_options(tmp_path, monkeypatch):
    batch = tmp_path / "batch.txt"
    batch.write_text("https://example.test/poc\n", encoding="utf-8")
    captured = {}
    monkeypatch.setattr(
        cli, "process_batch_file", lambda **kwargs: captured.update(kwargs)
    )

    result = RUNNER.invoke(
        cli.app,
        [
            "--batch",
            str(batch),
            "--dry-run",
            "--curate",
            "--dashboard",
            "--diff",
            "--scaffold",
            "--scaffold-output",
            str(tmp_path / "scaffolds"),
            "--vuln-scan",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert captured["curate"] is True
    assert captured["show_dashboard"] is True
    assert captured["diff_previous"] is True
    assert captured["scaffold"] is True
    assert captured["scaffold_output"] == tmp_path / "scaffolds"
    assert captured["vulnerability_scan"] is True


def test_batch_applies_feature_options_per_item(tmp_path, monkeypatch):
    batch = tmp_path / "batch.txt"
    batch.write_text("https://example.test/one\n", encoding="utf-8")
    calls = []
    monkeypatch.setattr(
        cli, "process_single_url", lambda **kwargs: calls.append(kwargs)
    )

    cli.process_batch_file(
        batch_path=batch,
        provider="local",
        api_key=None,
        model="model",
        temperature=0.2,
        base_url=None,
        output_dir=tmp_path / "reports",
        risk_level="High",
        target_os="Linux",
        include_mitigations=True,
        no_ingest=True,
        curate=True,
        show_dashboard=True,
        diff_previous=True,
        scaffold=True,
        scaffold_output=tmp_path / "scaffolds",
        vulnerability_scan=True,
    )

    assert calls[0]["curate"] is True
    assert calls[0]["show_dashboard"] is True
    assert calls[0]["diff_previous"] is True
    assert calls[0]["vulnerability_scan"] is True
    assert calls[0]["scaffold_output"] == (
        tmp_path / "scaffolds" / "https-example-test-one-blueprint"
    )


def test_workflow_cli_round_trip_and_invalid_payload(tmp_path):
    state_path = tmp_path / "workflow.json"
    created = RUNNER.invoke(cli.app, ["workflow-init", "--state", str(state_path)])
    status = RUNNER.invoke(cli.app, ["workflow-status", "--state", str(state_path)])
    applied = RUNNER.invoke(
        cli.app,
        [
            "workflow-apply",
            "--state",
            str(state_path),
            "--command",
            "decide",
            "--payload",
            '{"key":"scope_defined","value":true}',
        ],
    )
    invalid = RUNNER.invoke(
        cli.app,
        [
            "workflow-apply",
            "--state",
            str(state_path),
            "--command",
            "decide",
            "--payload",
            "[]",
        ],
    )

    assert created.exit_code == status.exit_code == applied.exit_code == 0
    assert invalid.exit_code == 2
    assert "payload must be a JSON object" in invalid.stdout
    help_text = RUNNER.invoke(cli.app, ["workflow-apply", "--help"]).stdout
    assert "confirm_scope" not in help_text
    assert "--command decide" in help_text
    unsupported = RUNNER.invoke(
        cli.app,
        [
            "workflow-apply",
            "--state",
            str(state_path),
            "--command",
            "confirm_scope",
            "--payload",
            "{}",
        ],
    )
    assert unsupported.exit_code == 2
    assert "Unsupported workflow command" in unsupported.stdout


def test_auxiliary_cli_commands_cover_success_and_error_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert RUNNER.invoke(cli.app, ["init"]).exit_code == 0
    assert RUNNER.invoke(cli.app, ["init"]).exit_code == 2
    assert RUNNER.invoke(cli.app, ["init", "--force"]).exit_code == 0

    demo_calls = []
    monkeypatch.setattr(cli, "demo", lambda: demo_calls.append(True))
    assert RUNNER.invoke(cli.app, ["explore", "--run"]).exit_code == 0
    assert demo_calls == [True]

    report_a = tmp_path / "old.md"
    report_b = tmp_path / "new.md"
    report_a.write_text("# Old\n", encoding="utf-8")
    report_b.write_text("# New\n", encoding="utf-8")
    diff_path = tmp_path / "nested" / "report.diff"
    assert (
        RUNNER.invoke(
            cli.app,
            ["diff", str(report_a), str(report_b), "--output", str(diff_path)],
        ).exit_code
        == 0
    )
    assert diff_path.is_file()
    assert (
        RUNNER.invoke(cli.app, ["export", str(report_b), "--format", "json"]).exit_code
        == 0
    )
    assert (
        RUNNER.invoke(
            cli.app,
            [
                "scaffold",
                "--report",
                str(report_b),
                "--output",
                str(tmp_path / "blueprint"),
            ],
        ).exit_code
        == 0
    )
    assert (
        RUNNER.invoke(cli.app, ["history", "--output-dir", str(tmp_path)]).exit_code
        == 0
    )


def test_compare_plugins_vulnerabilities_and_publish_commands(tmp_path, monkeypatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "app.py").write_text("print(1)\n", encoding="utf-8")
    (second / "app.js").write_text("console.log(1)\n", encoding="utf-8")
    comparison = tmp_path / "nested" / "comparison.md"
    compared = RUNNER.invoke(
        cli.app,
        ["compare", str(first), str(second), "--output", str(comparison)],
    )
    assert compared.exit_code == 0 and comparison.is_file()

    monkeypatch.setattr(cli, "registered_plugins", lambda: ["example"])
    assert "example" in RUNNER.invoke(cli.app, ["plugins"]).stdout

    monkeypatch.setattr(cli, "scan_path", lambda path: ([{"name": "pkg"}], []))
    assert RUNNER.invoke(cli.app, ["vulnerabilities", str(tmp_path)]).exit_code == 0

    report = tmp_path / "report.md"
    report.write_text("# Report\n", encoding="utf-8")
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "https://gist.test/1\n", ""
        ),
    )
    published = RUNNER.invoke(cli.app, ["publish", str(report), "--public"])
    assert published.exit_code == 0
    assert "https://gist.test/1" in published.stdout

    def fail_publish(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1,
            args[0],
            stderr=(
                "authentication failed: " "OPENAI_API_KEY=sk-test-1234567890abcdef"
            ),
        )

    monkeypatch.setattr(cli.subprocess, "run", fail_publish)
    failed = RUNNER.invoke(cli.app, ["publish", str(report)])
    assert failed.exit_code == 1
    assert "authentication failed" in failed.stdout
    assert "sk-test-1234567890abcdef" not in failed.stdout
    assert "[REDACTED]" in failed.stdout
    assert "ingesting" not in failed.stdout


def test_setup_reports_safe_dry_run_failure(monkeypatch):
    answers = iter(("local", "http://127.0.0.1:11434/v1"))
    events = []
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: next(answers))
    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(cli, "run_preflight", lambda **kwargs: None)
    monkeypatch.setattr(
        cli,
        "process_single_url",
        lambda **kwargs: (_ for _ in ()).throw(typer.Exit(7)),
    )

    with cli.capture_events(events.append):
        cli.setup()

    assert any(
        event["event"] == "setup_dry_run_failed" and "exit code 7" in event["message"]
        for event in events
    )


def test_cli_helper_error_and_platform_paths(tmp_path, monkeypatch):
    original_platform = cli.sys.platform
    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setattr(cli.typer_rich_utils, "FORCE_TERMINAL", True)
    cli.configure_platform_help()
    assert cli.typer_rich_utils.FORCE_TERMINAL is False

    calls = []
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    monkeypatch.setattr(
        cli.subprocess, "run", lambda command, **kwargs: calls.append(command)
    )
    assert cli.open_in_default_viewer(tmp_path / "report.md") is True
    assert calls[-1][0] == "open"
    monkeypatch.setattr(cli.sys, "platform", "linux")
    assert cli.open_in_default_viewer(tmp_path / "report.md") is True
    assert calls[-1][0] == "xdg-open"
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    assert cli.open_in_default_viewer(tmp_path / "report.md") is False
    monkeypatch.setattr(cli.sys, "platform", original_platform)

    assert "timed out" in cli.friendly_error_message(
        subprocess.TimeoutExpired(["tool"], 1)
    )
    assert "required file" in cli.friendly_error_message(FileNotFoundError())
    assert "Git failed" in cli.friendly_error_message(
        subprocess.CalledProcessError(1, ["git"])
    )
    assert "credential" in cli.friendly_error_message(RuntimeError("401 unauthorized"))
    assert "rate limit" in cli.friendly_error_message(RuntimeError("429 rate limit"))
    assert "without a diagnostic" in cli.friendly_error_message(RuntimeError(""))


def test_cli_prompt_load_failure_and_output_reconfigure_errors(monkeypatch):
    class BrokenResource:
        def __truediv__(self, name):
            return self

        def read_text(self, **kwargs):
            raise OSError("missing prompt")

    events = []
    monkeypatch.setattr(cli, "files", lambda package: BrokenResource())
    with cli.capture_events(events.append):
        with pytest.raises(typer.Exit) as error:
            cli.load_prompt()
    assert error.value.exit_code == 1
    assert events[-1]["event"] == "error"

    class Stream:
        def reconfigure(self, **kwargs):
            raise OSError("unsupported")

    monkeypatch.setattr(cli.sys, "stdout", Stream())
    monkeypatch.setattr(cli.sys, "stderr", Stream())
    cli.configure_output("json", True)
    assert cli.output_format == "json" and cli.no_color_state is True


def test_cli_confirmation_interactive_cancel_and_accept(monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: False)
    with pytest.raises(typer.Exit) as error:
        cli.confirm_ingestion("content", "local", "unknown", False)
    assert error.value.exit_code == 0

    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: True)
    assert cli.confirm_ingestion("content", "local", "unknown", False) == "content"
    private_key = "-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----"
    assert "private-key material" in cli.detect_sensitive_input(private_key)


def test_cli_batch_and_recovery_error_paths(tmp_path, monkeypatch):
    common = dict(
        provider="local",
        api_key=None,
        model="model",
        temperature=0.2,
        base_url=None,
        output_dir=tmp_path,
        risk_level="High",
        target_os="Linux",
        include_mitigations=True,
        no_ingest=True,
    )
    with pytest.raises(typer.Exit) as missing:
        cli.process_batch_file(batch_path=tmp_path / "missing.txt", **common)
    assert missing.value.exit_code == 2

    empty = tmp_path / "empty.txt"
    empty.write_text("# comments only\n", encoding="utf-8")
    with pytest.raises(typer.Exit) as no_urls:
        cli.process_batch_file(batch_path=empty, **common)
    assert no_urls.value.exit_code == 2

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("bad json", encoding="utf-8")
    batch = tmp_path / "batch.txt"
    batch.write_text("https://example.test/item\n", encoding="utf-8")
    with pytest.raises(typer.Exit) as bad_state:
        cli.process_batch_file(batch_path=batch, state_path=corrupt, **common)
    assert bad_state.value.exit_code == 2

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    result = RUNNER.invoke(cli.app, ["batch-reset", "--batch-state", str(corrupt)])
    assert result.exit_code == 2
    result = RUNNER.invoke(
        cli.app,
        ["batch-reset", "--batch-state", str(tmp_path / "absent.json"), "--yes"],
    )
    assert result.exit_code == 0 and "nothing was reset" in result.stdout


def test_cli_auxiliary_failure_and_json_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert RUNNER.invoke(cli.app, ["--format", "json", "explore"]).exit_code == 0
    assert RUNNER.invoke(cli.app, ["models"]).exit_code == 0
    assert RUNNER.invoke(cli.app, ["config"]).exit_code == 0

    existing = tmp_path / "workflow.json"
    assert (
        RUNNER.invoke(cli.app, ["workflow-init", "--state", str(existing)]).exit_code
        == 0
    )
    assert (
        RUNNER.invoke(cli.app, ["workflow-init", "--state", str(existing)]).exit_code
        == 2
    )
    missing = RUNNER.invoke(
        cli.app, ["workflow-status", "--state", str(tmp_path / "none")]
    )
    assert missing.exit_code == 2
    assert "Workflow state not found" in missing.stdout
    corrupt = tmp_path / "broken-workflow.json"
    corrupt.write_text("{not json", encoding="utf-8")
    broken = RUNNER.invoke(cli.app, ["workflow-status", "--state", str(corrupt)])
    assert broken.exit_code == 2
    assert "Cannot load workflow state" in broken.stdout

    assert RUNNER.invoke(cli.app, ["compare", "only-one"]).exit_code == 2
    monkeypatch.setattr(
        cli,
        "scan_path",
        lambda path: (_ for _ in ()).throw(ValueError("bad response")),
    )
    assert RUNNER.invoke(cli.app, ["vulnerabilities", str(tmp_path)]).exit_code == 1

    report = tmp_path / "report.md"
    report.write_text("# report\n", encoding="utf-8")
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    assert RUNNER.invoke(cli.app, ["publish", str(report)]).exit_code == 2
    monkeypatch.setattr(cli.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(args[0], 30)
        ),
    )
    assert RUNNER.invoke(cli.app, ["publish", str(report)]).exit_code == 1
    monkeypatch.setattr(
        cli.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("cannot execute")),
    )
    assert RUNNER.invoke(cli.app, ["publish", str(report)]).exit_code == 1


def test_cli_main_project_config_and_input_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / ".pocarchitect.toml"
    config.write_text('[defaults]\nprovider = "invalid"\n', encoding="utf-8")
    assert (
        RUNNER.invoke(cli.app, ["--url", "example.test/x", "--dry-run"]).exit_code == 2
    )

    config.write_text('[defaults]\nreport_format = "docx"\n', encoding="utf-8")
    assert (
        RUNNER.invoke(cli.app, ["--url", "example.test/x", "--dry-run"]).exit_code == 2
    )

    config.write_text('[defaults]\noutput_dir = "nested/reports"\n', encoding="utf-8")
    captured = {}
    monkeypatch.setattr(
        cli, "process_single_url", lambda **kwargs: captured.update(kwargs)
    )
    result = RUNNER.invoke(cli.app, ["--source", "https://example.test/x", "--dry-run"])
    assert result.exit_code == 0
    assert captured["output_dir"] == tmp_path / "nested/reports"

    local = tmp_path / "source"
    local.mkdir()
    result = RUNNER.invoke(cli.app, ["--path", str(local), "--dry-run"])
    assert result.exit_code == 0 and captured["local_path"] == local

    assert (
        RUNNER.invoke(cli.app, ["--url", "x", "--source", "y", "--dry-run"]).exit_code
        == 2
    )
    assert RUNNER.invoke(cli.app, ["--dry-run"]).exit_code == 2
    assert (
        RUNNER.invoke(
            cli.app, ["--url", "https://github.com/owner", "--dry-run"]
        ).exit_code
        == 2
    )


def test_cli_suggests_commands_and_resolves_default_batch_state(tmp_path, monkeypatch):
    command = typer.main.get_command(cli.app)
    with pytest.raises(cli.click.UsageError, match="Did you mean 'models'"):
        command.resolve_command(cli.click.Context(command), ["modles"])

    expected = tmp_path / "reports" / "batch_progress.json"
    expected.parent.mkdir()
    expected.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert (
        cli.resolve_batch_state_path(cli.DEFAULT_BATCH_STATE) == cli.DEFAULT_BATCH_STATE
    )


def test_cli_windows_viewer_and_gui_browser_timer(tmp_path, monkeypatch):
    starts = []
    original_platform = cli.sys.platform
    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setattr(
        cli.os, "startfile", lambda path: starts.append(path), raising=False
    )
    assert cli.open_in_default_viewer(tmp_path / "report.md") is True
    assert starts
    monkeypatch.setattr(cli.sys, "platform", original_platform)

    class Timer:
        daemon = False

        def __init__(self, delay, callback, args):
            self.args = args

        def start(self):
            starts.append(self.args[0])

    monkeypatch.setattr(cli.threading, "Timer", Timer)
    monkeypatch.setattr("pocarchitect.gui.create_app", lambda **kwargs: object())
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: None)
    result = RUNNER.invoke(cli.app, ["gui", "--port", "9124"])
    assert result.exit_code == 0
    assert any(str(value).startswith("http://127.0.0.1:9124/") for value in starts)


def test_cli_curation_interactive_validation(monkeypatch):
    files = [("one.py", "one", 3), ("two.py", "two", 3)]
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    with pytest.raises(typer.Exit) as noninteractive:
        cli.curate_grounding_files(files, True)
    assert noninteractive.value.exit_code == 2

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: "")
    assert cli.curate_grounding_files(files, True) == files
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: "bad")
    with pytest.raises(typer.Exit):
        cli.curate_grounding_files(files, True)
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: "3")
    with pytest.raises(typer.Exit):
        cli.curate_grounding_files(files, True)
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: "2")
    assert cli.curate_grounding_files(files, True) == [files[0]]


def test_cli_grounding_missing_directory_and_bounded_failure(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    result = cli.build_grounding_context("local", local_path=missing)
    assert result.ingestion == "url-only-ingestion-failed"

    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(cli, "MAX_REPOSITORY_FILES_SCANNED", 0)
    result = cli.build_grounding_context("local", local_path=source)
    assert result.ingestion == "url-only-ingestion-failed"


def test_cli_provider_variants_empty_response_and_unsupported(monkeypatch):
    clients = []

    class Completions:
        def __init__(self, content):
            self.content = content

        def create(self, **kwargs):
            message = type("Message", (), {"content": self.content})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    class Client:
        def __init__(self, content, **kwargs):
            self.chat = type("Chat", (), {"completions": Completions(content)})()
            self.kwargs = kwargs
            self.closed = False

        def close(self):
            self.closed = True

    content = {"value": " result "}

    def factory(**kwargs):
        client = Client(content["value"], **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(cli, "OpenAI", factory)
    for provider in ("local", "xai", "openai", "groq"):
        assert (
            cli.get_llm_response(provider, None, "model", 0.2, None, "s", "u")
            == "result"
        )
    assert all(client.closed for client in clients)
    assert clients[1].kwargs["base_url"] == "https://api.x.ai/v1"
    assert clients[3].kwargs["base_url"] == "https://api.groq.com/openai/v1"

    content["value"] = None
    with pytest.raises(typer.Exit):
        cli.get_llm_response("local", None, "model", 0.2, None, "s", "u")
    with pytest.raises(typer.Exit):
        cli.get_llm_response("unsupported", None, "model", 0.2, None, "s", "u")


def test_process_single_url_optional_outputs_and_text_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run_plugins", lambda *args: ["plugin evidence"])
    monkeypatch.setattr(cli, "extract_dependencies", lambda text: [{"name": "demo"}])
    monkeypatch.setattr(cli, "query_osv", lambda packages: [{"id": "OSV-1"}])
    output = tmp_path / "reports"
    first = cli.process_single_url(
        url="https://example.test/source",
        provider="local",
        api_key=None,
        model="model",
        temperature=0.2,
        base_url=None,
        output_dir=output,
        risk_level="High",
        target_os="Linux",
        include_mitigations=True,
        no_ingest=True,
        dry_run=False,
        verbose=False,
        response_override="# First",
        report_format="json",
        scaffold_output=tmp_path / "blueprint",
        vulnerability_scan=True,
    )
    monkeypatch.setattr(cli, "find_previous_report", lambda *args: first)
    second = cli.process_single_url(
        url="https://example.test/source",
        provider="local",
        api_key=None,
        model="model",
        temperature=0.2,
        base_url=None,
        output_dir=output,
        risk_level="High",
        target_os="Linux",
        include_mitigations=True,
        no_ingest=True,
        dry_run=False,
        verbose=False,
        response_override="# Second",
        diff_previous=True,
        show_dashboard=True,
    )

    assert first.with_suffix(".json").is_file()
    assert (tmp_path / "blueprint").is_dir()
    assert second.with_suffix(".diff").is_file()


def _single_url_kwargs(tmp_path, **overrides):
    values = dict(
        url="https://example.test/source",
        provider="local",
        api_key=None,
        model="model",
        temperature=0.2,
        base_url=None,
        output_dir=tmp_path / "reports",
        risk_level="High",
        target_os="Linux",
        include_mitigations=True,
        no_ingest=True,
        dry_run=False,
        verbose=False,
        confirmed=True,
    )
    values.update(overrides)
    return values


def test_doctor_fix_repairs_output_directory_and_retries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = {"n": 0}

    def fake_preflight(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise SystemExit(1)

    monkeypatch.setattr(cli, "run_preflight", fake_preflight)
    target = tmp_path / "repaired-out"
    result = RUNNER.invoke(
        cli.app,
        [
            "--format",
            "json",
            "--no-color",
            "doctor",
            "--offline",
            "--fix",
            "--yes",
            "--output-dir",
            str(target),
        ],
    )

    assert result.exit_code == 0
    assert target.is_dir()
    assert calls["n"] == 2
    assert "Output directory is ready" in result.stdout


def test_doctor_fix_interactive_paths_and_repair_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "blocked-out"
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(
        cli, "run_preflight", lambda **kwargs: (_ for _ in ()).throw(SystemExit(1))
    )
    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: False)

    with pytest.raises(typer.Exit) as cancelled:
        cli.doctor(offline=True, fix=True, yes=False, output_dir=target)
    assert cancelled.value.exit_code == 1
    assert not target.exists()

    original_mkdir = Path.mkdir

    def fail_target(self, *args, **kwargs):
        if Path(self) == target:
            raise OSError("denied")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_target)
    events = []
    with cli.capture_events(events.append):
        with pytest.raises(typer.Exit) as failed:
            cli.doctor(offline=True, fix=True, yes=True, output_dir=target)
    assert failed.value.exit_code == 1
    assert any(
        "Could not repair output directory" in event["message"] for event in events
    )


def test_doctor_fix_stores_key_and_reports_missing_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)
    monkeypatch.setattr(
        cli,
        "run_preflight",
        lambda **kwargs: (_ for _ in ()).throw(SystemExit("failed")),
    )
    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: True)
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: "sk-doctor-key")
    events = []
    with cli.capture_events(events.append):
        with pytest.raises(typer.Exit) as error:
            cli.doctor(
                provider="openai",
                offline=False,
                fix=True,
                yes=True,
                output_dir=tmp_path / "out",
            )
    assert error.value.exit_code == 1
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-doctor-key" in env_text
    assert any("Stored OPENAI_API_KEY" in event["message"] for event in events)
    assert all("sk-doctor-key" not in event["message"] for event in events)
    assert any("Git is missing" in event["message"] for event in events)


def test_setup_non_tty_and_cloud_key_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    non_tty = RUNNER.invoke(cli.app, ["setup"])
    assert non_tty.exit_code == 2
    assert "Setup is interactive" in non_tty.stdout

    answers = iter(("bogus", "openai", "sk-setup-key-value"))
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: next(answers))
    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: False)
    monkeypatch.setattr(cli, "run_preflight", lambda **kwargs: None)
    cli.setup()
    saved = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=sk-setup-key-value" in saved

    cli._upsert_env_file(tmp_path / ".env", "OPENAI_API_KEY", "replaced")
    cli._upsert_env_file(tmp_path / ".env", "XAI_API_KEY", "added")
    updated = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=replaced" in updated
    assert "sk-setup-key-value" not in updated
    assert "XAI_API_KEY=added" in updated

    empty = iter(("openai", "   "))
    monkeypatch.setattr(cli.typer, "prompt", lambda *args, **kwargs: next(empty))
    with pytest.raises(typer.Exit) as error:
        cli.setup()
    assert error.value.exit_code == 2


def test_mask_secret_and_upsert_preserves_spacing_variants(tmp_path):
    assert cli._mask_secret(None) == "(unset)"
    assert cli._mask_secret("short") == "set (••••)"
    assert cli._mask_secret("abcdefghij") == "set (abcd…ij)"

    env_path = tmp_path / ".env"
    env_path.write_text("GROQ_API_KEY = old-value\nOTHER=keep\n", encoding="utf-8")
    cli._upsert_env_file(env_path, "GROQ_API_KEY", "new-value")
    text = env_path.read_text(encoding="utf-8")
    assert "GROQ_API_KEY=new-value" in text
    assert "OTHER=keep" in text
    assert "old-value" not in text
    if cli.os.name != "nt":
        assert cli.stat.S_IMODE(env_path.stat().st_mode) == 0o600

    with pytest.raises(ValueError, match="single line"):
        cli._upsert_env_file(env_path, "GROQ_API_KEY", "first\nINJECTED=value")
    with pytest.raises(ValueError, match="uppercase"):
        cli._upsert_env_file(env_path, "invalid-key", "value")
    assert list(tmp_path.glob("..env.*.tmp")) == []


def test_is_retryable_and_transient_provider_retry(monkeypatch):
    assert cli._is_retryable(typer.Exit(1)) is False
    assert cli._is_retryable(cli.FatalProviderError("bad model")) is False
    bad_request = RuntimeError("bad request")
    bad_request.status_code = 400
    assert cli._is_retryable(bad_request) is False
    rate_limited = RuntimeError("slow down")
    rate_limited.status_code = 429
    assert cli._is_retryable(rate_limited) is True
    timeout = RuntimeError("timeout")
    timeout.status_code = 408
    assert cli._is_retryable(timeout) is True
    assert cli._is_retryable(RuntimeError("401 unauthorized")) is False
    assert cli._is_retryable(RuntimeError("model not found")) is False
    assert cli._is_retryable(RuntimeError("connection reset")) is True

    calls = {"n": 0}

    class Completions:
        def create(self, **kwargs):
            calls["n"] += 1
            if calls["n"] < 3:
                error = RuntimeError("temporary")
                error.status_code = 429
                raise error
            message = type("Message", (), {"content": " recovered "})()
            choice = type("Choice", (), {"message": message})()
            return type("Response", (), {"choices": [choice]})()

    class Client:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": Completions()})()

        def close(self):
            return None

    monkeypatch.setattr(cli, "OpenAI", lambda **kwargs: Client())
    assert (
        cli.get_llm_response("openai", "sk-x", "gpt-4o", 0.2, None, "sys", "user")
        == "recovered"
    )
    assert calls["n"] == 3

    calls["n"] = 0

    class Permanent:
        def create(self, **kwargs):
            calls["n"] += 1
            error = RuntimeError("bad request")
            error.status_code = 400
            raise error

    class PermanentClient:
        def __init__(self, **kwargs):
            self.chat = type("Chat", (), {"completions": Permanent()})()

    monkeypatch.setattr(cli, "OpenAI", lambda **kwargs: PermanentClient())
    with pytest.raises(RuntimeError, match="bad request"):
        cli.get_llm_response("openai", "sk-x", "gpt-4o", 0.2, None, "sys", "user")
    assert calls["n"] == 1


def test_gui_command_reports_missing_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "uvicorn", None)
    result = RUNNER.invoke(cli.app, ["gui", "--no-open"])
    assert result.exit_code == 2
    assert "GUI dependencies are not installed" in result.stdout


def test_process_single_url_error_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "MAX_PROMPT_CHARACTERS", 10)
    with pytest.raises(typer.Exit) as oversized:
        cli.process_single_url(**_single_url_kwargs(tmp_path))
    assert oversized.value.exit_code == 2

    monkeypatch.setattr(cli, "MAX_PROMPT_CHARACTERS", 500_000)
    monkeypatch.setattr(cli, "extract_dependencies", lambda text: [{"name": "demo"}])
    monkeypatch.setattr(
        cli,
        "query_osv",
        lambda packages: (_ for _ in ()).throw(OSError("offline")),
    )
    events = []
    with cli.capture_events(events.append):
        cli.process_single_url(
            **_single_url_kwargs(
                tmp_path, vulnerability_scan=True, response_override="# ok"
            )
        )
    assert any(event["event"] == "vulnerability_scan_failed" for event in events)

    monkeypatch.setattr(
        cli,
        "get_llm_response",
        lambda **kwargs: (_ for _ in ()).throw(cli.FatalProviderError("unknown model")),
    )
    with pytest.raises(typer.Exit) as fatal:
        cli.process_single_url(**_single_url_kwargs(tmp_path))
    assert fatal.value.exit_code == 1

    monkeypatch.setattr(
        cli,
        "get_llm_response",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("provider broke")),
    )
    with pytest.raises(RuntimeError, match="provider broke"):
        cli.process_single_url(**_single_url_kwargs(tmp_path))


def test_save_report_cleans_temporary_file_and_reports_open_failure(
    tmp_path, monkeypatch
):
    grounding = cli.GroundingResult("content", "disabled")
    original_replace = os.replace
    monkeypatch.setattr(
        cli.os,
        "replace",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("denied")),
    )
    with pytest.raises(OSError, match="denied"):
        cli.save_report(
            "# Report\n",
            "https://example.test/x",
            tmp_path,
            "local",
            "model",
            grounding,
        )
    assert list(tmp_path.glob(".POCAnalysis_*")) == []

    monkeypatch.setattr(cli.os, "replace", original_replace)
    monkeypatch.setattr(cli, "open_in_default_viewer", lambda path: False)
    events = []
    with cli.capture_events(events.append):
        path = cli.save_report(
            "# Report\n",
            "https://example.test/x",
            tmp_path,
            "local",
            "model",
            grounding,
            open_report=True,
        )
    assert path.is_file()
    assert any(event["event"] == "report_open_failed" for event in events)


def test_batch_reset_interactive_confirm_and_compare_url_only(tmp_path, monkeypatch):
    ledger = tmp_path / "batch_progress.json"
    ledger.write_text(
        json.dumps(
            {"version": 2, "items": {"https://example.test/a": {"status": "success"}}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: False)
    events = []
    with cli.capture_events(events.append):
        with pytest.raises(typer.Exit) as cancelled:
            cli.batch_reset(batch_state=ledger, yes=False)
    assert cancelled.value.exit_code == 0
    assert any("was not reset" in event["message"] for event in events)
    assert ledger.is_file()

    monkeypatch.setattr(cli.typer, "confirm", lambda *args, **kwargs: True)
    events = []
    with cli.capture_events(events.append):
        cli.batch_reset(batch_state=ledger, yes=False)
    assert any("retained at" in event["message"] for event in events)
    assert not ledger.exists()

    compared = RUNNER.invoke(
        cli.app,
        ["compare", "https://example.test/a", "https://example.test/b"],
    )
    assert compared.exit_code == 0
    assert "URL-only" in compared.stdout
