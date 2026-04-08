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


def test_check_api_key_ignores_placeholder_values(tmp_path, monkeypatch):
    for key in preflight.ENV_KEY_NAMES:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=your_key_here\n", encoding="utf-8")

    ok, msg = preflight.check_api_key()
    assert ok is False
    assert msg == "✗ No API key found"


def test_check_api_key_accepts_real_env_file_value(tmp_path, monkeypatch):
    for key in preflight.ENV_KEY_NAMES:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test-123\n", encoding="utf-8")

    ok, msg = preflight.check_api_key()
    assert ok is True
    assert msg == "✓ OPENAI_API_KEY in .env"
