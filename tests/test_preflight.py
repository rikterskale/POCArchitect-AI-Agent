import json
import subprocess

from pocarchitect import preflight


def test_check_cli_command_uses_module_entrypoint_first(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output, check):
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

    def fake_run(cmd, capture_output, check):
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
    def fake_run(cmd, capture_output, check):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    ok, msg = preflight.check_cli_command()
    assert ok is False
    assert msg == "FAIL: Not found"


def test_check_api_key_ignores_placeholder_values(tmp_path, monkeypatch):
    for key in preflight.ENV_KEY_NAMES:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=your_key_here\n", encoding="utf-8")

    ok, msg = preflight.check_api_key()
    assert ok is False
    assert msg == "FAIL: No API key found"


def test_check_api_key_accepts_real_env_file_value(tmp_path, monkeypatch):
    for key in preflight.ENV_KEY_NAMES:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test-123\n", encoding="utf-8")

    ok, msg = preflight.check_api_key()
    assert ok is True
    assert msg == "OK: OPENAI_API_KEY in .env"


def test_offline_preflight_does_not_require_api_key(monkeypatch):
    monkeypatch.setattr(preflight, "check_dependency", lambda name: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight, "check_output_directory_writable", lambda: (True, "ok")
    )
    monkeypatch.setattr(
        preflight,
        "check_api_key",
        lambda: (_ for _ in ()).throw(
            AssertionError("API key check should be skipped")
        ),
    )

    preflight.main(require_api_key=False, offline=True)


def test_local_preflight_checks_endpoint_without_cloud_key(monkeypatch):
    monkeypatch.setattr(preflight, "check_dependency", lambda name: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight, "check_output_directory_writable", lambda: (True, "ok")
    )
    monkeypatch.setattr(
        preflight,
        "check_api_key",
        lambda provider: (_ for _ in ()).throw(
            AssertionError("Local provider must not require a cloud API key")
        ),
    )
    checked = []
    monkeypatch.setattr(
        preflight,
        "check_local_endpoint",
        lambda base_url: (checked.append(base_url) or True, "ok"),
    )

    preflight.main(provider="local", base_url="http://127.0.0.1:11434/v1")

    assert checked == ["http://127.0.0.1:11434/v1"]


def test_preflight_json_is_one_machine_readable_event(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "check_dependency", lambda name: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight, "check_output_directory_writable", lambda: (True, "ok")
    )

    preflight.main(
        require_api_key=False, offline=True, output_format="json", no_color=True
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["event"] == "preflight"
    assert payload["offline"] is True
    assert "\x1b" not in json.dumps(payload)
