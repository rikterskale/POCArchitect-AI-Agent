import json
import subprocess
from urllib.error import URLError

from pocarchitect import preflight


def test_check_cli_command_uses_module_entrypoint_first(monkeypatch):
    calls = []

    def fake_run(cmd, capture_output, check, timeout):
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

    def fake_run(cmd, capture_output, check, timeout):
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
    def fake_run(cmd, capture_output, check, timeout):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    ok, msg = preflight.check_cli_command()
    assert ok is False
    assert msg == "FAIL: Not found"


def test_check_cli_command_treats_timeout_as_unavailable(monkeypatch):
    def fake_run(cmd, capture_output, check, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

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
    monkeypatch.setattr(preflight, "check_git_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight,
        "check_output_directory_writable",
        lambda output_dir=None: (True, "ok"),
    )
    monkeypatch.setattr(
        preflight,
        "check_api_key",
        lambda: (_ for _ in ()).throw(
            AssertionError("API key check should be skipped")
        ),
    )

    preflight.main(require_api_key=False, offline=True)


def test_offline_preflight_does_not_require_git(monkeypatch):
    monkeypatch.setattr(preflight, "check_dependency", lambda name: (True, "ok"))
    monkeypatch.setattr(
        preflight,
        "check_git_command",
        lambda: (_ for _ in ()).throw(AssertionError("Git should be optional")),
    )
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight,
        "check_output_directory_writable",
        lambda output_dir=None: (True, "ok"),
    )

    preflight.main(require_api_key=False, offline=True, require_git=False)


def test_local_preflight_checks_endpoint_without_cloud_key(monkeypatch):
    monkeypatch.setattr(preflight, "check_dependency", lambda name: (True, "ok"))
    monkeypatch.setattr(preflight, "check_git_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight,
        "check_output_directory_writable",
        lambda output_dir=None: (True, "ok"),
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
    monkeypatch.setattr(preflight, "check_git_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight,
        "check_output_directory_writable",
        lambda output_dir=None: (True, "ok"),
    )

    preflight.main(
        require_api_key=False, offline=True, output_format="json", no_color=True
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["event"] == "preflight"
    assert payload["offline"] is True
    assert payload["diagnostic_version"] == 1
    assert all(row["code"] for row in payload["checks"])
    assert "\x1b" not in json.dumps(payload)


def test_output_directory_check_uses_explicit_path(tmp_path):
    output_dir = tmp_path / "chosen" / "reports"

    ok, message = preflight.check_output_directory_writable(output_dir)

    assert ok is True
    assert str(output_dir) in message
    assert output_dir.is_dir()
    assert not (output_dir / ".write_test").exists()


def test_output_directory_check_preserves_existing_files(tmp_path):
    marker = tmp_path / ".write_test"
    marker.write_text("operator data", encoding="utf-8")

    ok, _ = preflight.check_output_directory_writable(tmp_path)

    assert ok is True
    assert marker.read_text(encoding="utf-8") == "operator data"
    assert list(tmp_path.glob(".pocarchitect-write-test-*")) == []


def test_preflight_passes_output_directory_to_check(tmp_path, monkeypatch):
    checked = []
    monkeypatch.setattr(preflight, "check_dependency", lambda name: (True, "ok"))
    monkeypatch.setattr(preflight, "check_git_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_cli_command", lambda: (True, "ok"))
    monkeypatch.setattr(preflight, "check_prompt_file", lambda: (True, "ok"))
    monkeypatch.setattr(
        preflight,
        "check_output_directory_writable",
        lambda output_dir=None: (checked.append(output_dir) or True, "ok"),
    )

    preflight.main(
        require_api_key=False,
        offline=True,
        output_dir=tmp_path,
        output_format="json",
        no_color=True,
    )

    assert checked == [tmp_path]


def test_preflight_helpers_report_dependency_git_prompt_and_output_failures(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        preflight.importlib,
        "import_module",
        lambda name: (_ for _ in ()).throw(ImportError(name)),
    )
    assert preflight.check_dependency("missing") == (False, "FAIL: Missing")

    monkeypatch.setattr(preflight.shutil, "which", lambda name: None)
    assert preflight.check_git_command() == (
        False,
        "FAIL: Git executable not found",
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(preflight, "__file__", str(tmp_path / "preflight.py"))
    assert preflight.check_prompt_file() == (False, "FAIL: Prompt file missing")

    monkeypatch.setattr(
        preflight.tempfile,
        "mkstemp",
        lambda **kwargs: (_ for _ in ()).throw(PermissionError("denied")),
    )
    ok, message = preflight.check_output_directory_writable(tmp_path / "reports")
    assert ok is False
    assert "not writable" in message and "denied" in message


def test_local_endpoint_validation_and_failure_responses(monkeypatch):
    ok, message = preflight.check_local_endpoint("file:///tmp/model")
    assert ok is False and "http(s) URL" in message

    monkeypatch.setattr(
        preflight,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("offline")),
    )
    ok, message = preflight.check_local_endpoint("http://127.0.0.1:11434/v1")
    assert ok is False and "offline" in message

    class Response:
        status = 503

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(preflight, "urlopen", lambda *args, **kwargs: Response())
    ok, message = preflight.check_local_endpoint("http://127.0.0.1:11434/v1")
    assert ok is False and "unexpected response" in message
