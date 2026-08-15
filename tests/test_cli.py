import io
import json
import os
import subprocess

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from pocarchitect import cli

RUNNER = CliRunner()


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
