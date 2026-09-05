import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pocarchitect import cli, verification

RUNNER = CliRunner()


def python_project(tmp_path: Path, *, ready: bool = True) -> tuple[Path, Path]:
    project = tmp_path / "authorized-poc"
    (project / "tests").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        '[project]\nname = "authorized-poc"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    (project / "tests" / "test_acceptance.py").write_text(
        "import unittest\n\n"
        "class Acceptance(unittest.TestCase):\n"
        "    def test_lab_contract(self):\n"
        "        self.assertEqual(2 + 2, 4)\n",
        encoding="utf-8",
    )
    contract = project / ".pocarchitect" / verification.CONTRACT_FILENAME
    verification.create_contract(
        project,
        contract,
        authorization="ACME isolated validation lab",
        ready=ready,
        test_commands=(["python -m unittest discover -s tests -v"] if ready else ()),
    )
    return project, contract


def completed(
    arguments: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(arguments, returncode, stdout, stderr)


def successful_docker(monkeypatch, *, fail_command: str | None = None):
    calls: list[list[str]] = []

    def fake_run(arguments, *, timeout):
        command = list(arguments)
        calls.append(command)
        if command[1:2] == ["info"]:
            return completed(command, stdout="26.1.0\n")
        if command[1:3] == ["image", "inspect"]:
            return completed(command, stdout="sha256:reviewed-image\n")
        if command[1:2] == ["run"]:
            return completed(command, stdout="container-id\n")
        if command[1:2] == ["rm"]:
            return completed(command)
        if fail_command is not None and command[-1] == fail_command:
            return completed(
                command, returncode=7, stderr="contract assertion failed\n"
            )
        return completed(command, stdout="ok\n")

    monkeypatch.setattr(verification.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(verification, "_run_host", fake_run)
    monkeypatch.setattr(
        verification,
        "_run_host_bounded",
        lambda arguments, *, timeout: (fake_run(arguments, timeout=timeout), False),
    )
    return calls


def test_contract_starts_draft_and_requires_explicit_readiness(tmp_path):
    project, contract = python_project(tmp_path, ready=False)
    document = json.loads(contract.read_text(encoding="utf-8"))

    assert document["implementation_status"] == "draft"
    assert document["test_commands"] == ["python -m unittest discover -s tests -v"]
    assert (
        verification.load_contract(contract, require_ready=False).project_name
        == project.name
    )
    with pytest.raises(verification.ContractError, match="still draft"):
        verification.load_contract(contract)
    if os.name != "nt":
        assert contract.stat().st_mode & 0o777 == 0o600


def test_ready_contract_requires_an_authorized_scope(tmp_path):
    project = tmp_path / "poc"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='poc'\nversion='1'\n")
    contract = project / verification.CONTRACT_FILENAME
    with pytest.raises(verification.ContractError, match="approved lab scope"):
        verification.create_contract(project, contract, ready=True)
    assert not contract.exists()


def test_ready_contract_requires_an_explicit_test_command(tmp_path):
    project = tmp_path / "poc"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='poc'\nversion='1'\n", encoding="utf-8"
    )
    contract = project / verification.CONTRACT_FILENAME

    with pytest.raises(verification.ContractError, match="explicit test command"):
        verification.create_contract(
            project,
            contract,
            authorization="approved isolated lab",
            ready=True,
        )

    assert not contract.exists()


def test_custom_contract_supports_an_explicit_unknown_toolchain(tmp_path):
    project = tmp_path / "custom"
    project.mkdir()
    contract = project / "contract.json"

    verification.create_contract(
        project,
        contract,
        image="vendor/toolchain@sha256:abc123",
        test_commands=["./verify-poc"],
        authorization="customer-owned lab",
        ready=True,
    )

    loaded = verification.load_contract(contract)
    assert loaded.image == "vendor/toolchain@sha256:abc123"
    assert loaded.test_commands == ("./verify-poc",)


def test_contract_rejects_artifacts_outside_the_project(tmp_path):
    _, contract = python_project(tmp_path)
    document = json.loads(contract.read_text(encoding="utf-8"))
    document["required_artifacts"] = ["../host-secret"]
    contract.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(verification.ContractError, match="contained by the project"):
        verification.load_contract(contract)


def test_contract_rejects_unknown_fields_and_non_posix_artifact_paths(tmp_path):
    _, contract = python_project(tmp_path)
    document = json.loads(contract.read_text(encoding="utf-8"))
    document["typo_test_command"] = ["true"]
    contract.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(verification.ContractError, match="unsupported fields"):
        verification.load_contract(contract)

    document.pop("typo_test_command")
    document["required_artifacts"] = [r"C:\\host-secret"]
    contract.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(verification.ContractError, match="contained by the project"):
        verification.load_contract(contract)


@pytest.mark.skipif(os.name == "nt", reason="symlinks require elevated Windows rights")
def test_forced_contract_replacement_does_not_follow_a_symlink(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='project'\nversion='1'\n", encoding="utf-8"
    )
    victim = tmp_path / "victim.json"
    victim.write_text('{"keep": true}\n', encoding="utf-8")
    contract = project / verification.CONTRACT_FILENAME
    contract.symlink_to(victim)

    verification.create_contract(
        project,
        contract,
        authorization="isolated lab",
        force=True,
    )

    assert not contract.is_symlink()
    assert json.loads(victim.read_text(encoding="utf-8")) == {"keep": True}


def test_sandbox_command_enforces_the_runtime_boundary(tmp_path):
    arguments = verification._sandbox_arguments(
        container_name="pocarchitect-verify-test",
        verification_id="test",
        snapshot=tmp_path,
        image="python:3.12-slim",
    )
    rendered = " ".join(arguments)

    assert "--network=none" in arguments
    assert "--read-only" in arguments
    assert "--cap-drop=ALL" in arguments
    assert "--security-opt=no-new-privileges" in arguments
    assert "--pull=never" in arguments
    assert "--user=65534:65534" in arguments
    assert "--pids-limit=128" in arguments
    assert "--memory=512m" in arguments
    assert "target=/source,readonly" in rendered
    assert "/var/run/docker.sock" not in rendered


def test_untrusted_step_output_is_capped_while_the_process_runs():
    completed_process, timed_out = verification._run_host_bounded(
        [
            sys.executable,
            "-c",
            "import os; os.write(1, b'\\xff' * 100000); os.write(2, b'\\xfe' * 100000)",
        ],
        timeout=10,
    )

    assert timed_out is False
    assert completed_process.returncode == 0
    assert len(completed_process.stdout.encode("utf-8")) <= verification.MAX_LOG_BYTES
    assert len(completed_process.stderr.encode("utf-8")) <= verification.MAX_LOG_BYTES
    assert completed_process.stdout.endswith("[output truncated by POCArchitect]\n")
    assert completed_process.stderr.endswith("[output truncated by POCArchitect]\n")


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode normalization")
def test_snapshot_is_readable_by_the_non_root_sandbox_and_binds_modes(tmp_path):
    project = tmp_path / "private-project"
    private_directory = project / "src"
    private_directory.mkdir(parents=True, mode=0o700)
    source = private_directory / "poc.py"
    source.write_text("print('verified')\n", encoding="utf-8")
    source.chmod(0o600)
    executable = project / "verify.sh"
    executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    executable.chmod(0o700)
    (project / "empty").mkdir(mode=0o700)

    first = tmp_path / "first-snapshot"
    first_digest, _ = verification._copy_snapshot(project, first)

    assert stat.S_IMODE(first.stat().st_mode) == 0o755
    assert stat.S_IMODE((first / "src").stat().st_mode) == 0o755
    assert stat.S_IMODE((first / "src" / "poc.py").stat().st_mode) == 0o644
    assert stat.S_IMODE((first / "verify.sh").stat().st_mode) == 0o755
    assert stat.S_IMODE((first / "empty").stat().st_mode) == 0o755

    executable.chmod(0o600)
    second = tmp_path / "second-snapshot"
    second_digest, _ = verification._copy_snapshot(project, second)

    assert first_digest != second_digest


def test_successful_verification_writes_complete_private_evidence(
    tmp_path, monkeypatch
):
    project, contract = python_project(tmp_path)
    (project / ".env").write_text("SECRET=never-copy-this\n", encoding="utf-8")
    document = json.loads(contract.read_text(encoding="utf-8"))
    document["required_artifacts"] = ["pyproject.toml"]
    contract.write_text(json.dumps(document), encoding="utf-8")
    calls = successful_docker(monkeypatch)
    evidence = tmp_path / "evidence" / "result.json"

    result = verification.run_verification(project, contract, evidence)

    assert result.status == "verified"
    assert result.image_id == "sha256:reviewed-image"
    assert result.excluded_paths == (".env",)
    assert [step.name for step in result.steps] == [
        "prepare",
        "build:1",
        "test:1",
        "artifact:pyproject.toml",
        "cleanup",
    ]
    assert all(step.passed for step in result.steps)
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["status"] == "verified"
    assert payload["sandbox"]["network"] == "none"
    assert payload["sandbox"]["implicit_image_pull"] is False
    assert payload["authorization"] == "ACME isolated validation lab"
    assert "SECRET=never-copy-this" not in evidence.read_text(encoding="utf-8")
    assert any(call[1:3] == ["rm", "--force"] for call in calls)
    if os.name != "nt":
        assert evidence.stat().st_mode & 0o777 == 0o600


def test_failed_test_is_not_reported_as_verified_and_container_is_removed(
    tmp_path, monkeypatch
):
    project, contract = python_project(tmp_path)
    failed_command = "python -m unittest discover -s tests -v"
    calls = successful_docker(monkeypatch, fail_command=failed_command)
    evidence = tmp_path / "failed.json"

    result = verification.run_verification(project, contract, evidence)

    assert result.status == "failed"
    assert result.steps[-2].name == "test:1"
    assert result.steps[-2].exit_code == 7
    assert result.steps[-1].name == "cleanup"
    assert result.steps[-1].passed is True
    assert json.loads(evidence.read_text(encoding="utf-8"))["status"] == "failed"
    assert any(call[1:3] == ["rm", "--force"] for call in calls)


def test_failed_cleanup_prevents_a_verified_result(tmp_path, monkeypatch):
    project, contract = python_project(tmp_path)
    calls = successful_docker(monkeypatch)
    original = verification._run_host

    def fail_cleanup(arguments, *, timeout):
        command = list(arguments)
        if command[1:2] == ["rm"]:
            calls.append(command)
            return completed(command, returncode=1, stderr="daemon cleanup failed")
        return original(arguments, timeout=timeout)

    monkeypatch.setattr(verification, "_run_host", fail_cleanup)
    evidence = tmp_path / "cleanup-failed.json"

    result = verification.run_verification(project, contract, evidence)

    assert result.status == "failed"
    assert result.steps[-1].name == "cleanup"
    assert result.steps[-1].passed is False
    assert "daemon cleanup failed" in result.steps[-1].stderr


def test_verification_never_overwrites_existing_evidence(tmp_path, monkeypatch):
    project, contract = python_project(tmp_path)
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"retained": true}\n', encoding="utf-8")
    monkeypatch.setattr(
        verification.shutil,
        "which",
        lambda name: pytest.fail("runtime must not be checked"),
    )

    with pytest.raises(verification.VerificationError, match="already exists"):
        verification.run_verification(project, contract, evidence)

    assert json.loads(evidence.read_text(encoding="utf-8")) == {"retained": True}


def test_missing_image_fails_without_an_implicit_pull(tmp_path, monkeypatch):
    project, contract = python_project(tmp_path)

    def fake_run(arguments, *, timeout):
        command = list(arguments)
        if command[1:2] == ["info"]:
            return completed(command, stdout="26.1.0\n")
        return completed(command, returncode=1, stderr="No such image\n")

    monkeypatch.setattr(verification.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(verification, "_run_host", fake_run)

    with pytest.raises(verification.RuntimeUnavailableError, match="docker pull"):
        verification.run_verification(project, contract, tmp_path / "evidence.json")


def test_verify_init_cli_creates_a_reviewable_draft(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        "[project]\nname='project'\nversion='1'\n", encoding="utf-8"
    )

    result = RUNNER.invoke(cli.app, ["verify", "init", str(project)])

    assert result.exit_code == 0, result.stdout
    assert "contract created (draft)" in result.stdout
    assert (project / ".pocarchitect" / verification.CONTRACT_FILENAME).is_file()


def test_verify_run_cli_requires_confirmation_before_execution(tmp_path, monkeypatch):
    project, _ = python_project(tmp_path)
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("verification must not start")

    monkeypatch.setattr(cli, "run_verification", forbidden)
    result = RUNNER.invoke(cli.app, ["verify", "run", str(project)])

    assert result.exit_code == 2
    assert "rerun with --yes" in result.stdout
    assert called is False


def test_verify_run_cli_emits_a_machine_readable_success(tmp_path, monkeypatch):
    project, _ = python_project(tmp_path)
    evidence = tmp_path / "result.json"
    fake_result = verification.VerificationResult(
        verification_id="abc123",
        status="verified",
        started_at="2026-09-05T00:00:00+00:00",
        finished_at="2026-09-05T00:00:01+00:00",
        project_name=project.name,
        authorization="ACME lab",
        source_sha256="source-digest",
        contract_sha256="contract-digest",
        image="python:3.12-slim",
        image_id="sha256:image",
        evidence_path=evidence,
        sandbox={"network": "none"},
        excluded_paths=(),
        steps=(
            verification.StepResult(
                name="test:1",
                command="python -m unittest",
                exit_code=0,
                duration_seconds=0.1,
                passed=True,
                timed_out=False,
                stdout="ok",
                stderr="",
            ),
        ),
    )
    monkeypatch.setattr(cli, "run_verification", lambda *args, **kwargs: fake_result)

    result = RUNNER.invoke(
        cli.app,
        ["--format", "json", "verify", "run", str(project), "--yes"],
    )

    assert result.exit_code == 0, result.stdout
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [event["event"] for event in events] == [
        "verification_started",
        "poc_verified",
    ]
    assert events[-1]["status"] == "verified"
