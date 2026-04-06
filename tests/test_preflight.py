import subprocess

from pocarchitect import preflight


def test_check_cli_command_uses_module_entrypoint_first(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output, check):  # noqa: ANN001
        calls.append(cmd)
        if cmd[:3] == [preflight.sys.executable, "-m", "pocarchitect"]:
            return subprocess.CompletedProcess(cmd, 0)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    ok, msg = preflight.check_cli_command()
    assert ok is True
    assert "Available via" in msg
    assert calls[0][:3] == [preflight.sys.executable, "-m", "pocarchitect"]


def test_check_cli_command_falls_back_to_cli_binary(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output, check):  # noqa: ANN001
        calls.append(cmd)
        if cmd[0] == "pocarchitect":
            return subprocess.CompletedProcess(cmd, 0)
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    ok, msg = preflight.check_cli_command()
    assert ok is True
    assert "pocarchitect --help" in msg
    assert calls[0][:3] == [preflight.sys.executable, "-m", "pocarchitect"]


def test_check_cli_command_reports_not_found(monkeypatch):
    def fake_run(cmd, capture_output, check):  # noqa: ANN001
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    ok, msg = preflight.check_cli_command()
    assert ok is False
    assert msg == "✗ Not found"