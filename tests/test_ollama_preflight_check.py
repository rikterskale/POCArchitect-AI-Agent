import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError, URLError

from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "docs" / "ollama_preflight_check.py"


def load_helper():
    spec = importlib.util.spec_from_file_location("ollama_preflight_check", HELPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_helper_success_reports_only_the_three_bounded_checks(monkeypatch):
    helper = load_helper()
    output = io.StringIO()
    helper.console = Console(file=output, force_terminal=False, color_system=None)
    monkeypatch.setattr(helper, "check_ollama_running", lambda: (True, "server ok"))
    monkeypatch.setattr(helper, "check_model_available", lambda: (True, "model ok"))
    monkeypatch.setattr(
        helper,
        "check_openai_compatible_endpoint",
        lambda: (True, "chat endpoint ok"),
    )

    result = helper.main()
    text = output.getvalue()

    assert result == 0
    assert "THE THREE LISTED OLLAMA CHECKS PASSED" in text
    assert helper.OLLAMA_URL in text
    assert helper.TEST_MODEL in text
    assert "PERFECTLY READY" not in text
    assert "full prompt" in text


def test_helper_request_json_uses_standard_library_transport(monkeypatch):
    helper = load_helper()

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"version": "0.1"}'

    captured = {}

    def fake_urlopen(request, timeout):
        captured["method"] = request.method
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(helper, "urlopen", fake_urlopen)
    status, payload = helper.request_json("GET", "/api/version", timeout=3)

    assert status == 200
    assert payload == {"version": "0.1"}
    assert captured == {"method": "GET", "timeout": 3}


def test_helper_check_functions_cover_health_and_failure_responses(monkeypatch):
    helper = load_helper()

    monkeypatch.setattr(
        helper, "request_json", lambda *args, **kwargs: (200, {"version": "1.2.3"})
    )
    assert helper.check_ollama_running()[0] is True
    assert helper.check_model_available()[0] is True
    assert helper.check_openai_compatible_endpoint()[0] is True

    monkeypatch.setattr(helper, "request_json", lambda *args, **kwargs: (503, {}))
    assert helper.check_ollama_running()[0] is False
    assert helper.check_model_available()[0] is False
    assert helper.check_openai_compatible_endpoint()[0] is False

    monkeypatch.setattr(
        helper,
        "request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    assert "offline" in helper.check_ollama_running()[1]
    assert "offline" in helper.check_model_available()[1]
    assert "offline" in helper.check_openai_compatible_endpoint()[1]


def test_helper_request_json_translates_http_and_url_errors(monkeypatch):
    helper = load_helper()
    monkeypatch.setattr(
        helper,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            HTTPError("http://local", 404, "missing", {}, None)
        ),
    )
    assert helper.request_json("GET", "/missing", timeout=1) == (404, {})

    monkeypatch.setattr(
        helper,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError("offline")),
    )
    try:
        helper.request_json("GET", "/missing", timeout=1)
    except OSError as error:
        assert "offline" in str(error)
    else:
        raise AssertionError("Expected URL errors to become OSError")


def test_helper_main_returns_failure_when_any_check_fails():
    helper = load_helper()
    helper.console = Console(
        file=io.StringIO(), force_terminal=False, color_system=None
    )
    helper.check_ollama_running = lambda: (True, "ok")
    helper.check_model_available = lambda: (False, "missing")
    helper.check_openai_compatible_endpoint = lambda: (True, "ok")

    assert helper.main() == 1
