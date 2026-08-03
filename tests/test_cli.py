import io
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

    text = output.getvalue()
    assert "total=2 processed=2 success=1 failed=1 skipped=0" in text
    assert "https://github.com/example/bad" in text


def test_process_batch_file_dry_run_reports_skipped_count(tmp_path, monkeypatch):
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
    assert "total=2 processed=1 success=1 failed=0 skipped=1" in text
    assert "Dry-run mode processed only the first URL by design." in text


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

    assert result.exit_code == 1
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

    text = output.getvalue()
    assert "total=2 processed=2 success=1 failed=1 skipped=0" in text
    assert "https://github.com/example/exit" in text


def test_build_grounding_context_uses_non_interactive_timed_git_clone(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    context = cli.build_grounding_context("https://github.com/octocat/Hello-World")

    assert "Repository: octocat/Hello-World" in context
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
        True,
    )

    text = report.read_text(encoding="utf-8")
    assert 'source_url: "https://github.com/example/repo"' in text
    assert 'provider: "local"' in text
    assert "content_sha256:" in text
    assert "test-model" in text


def test_sensitive_input_detection_does_not_return_secret():
    secret = "OPENAI_API_KEY=sk-test-1234567890abcdef"
    categories = cli.detect_sensitive_input(secret)
    assert categories
    assert all("sk-test" not in category for category in categories)
