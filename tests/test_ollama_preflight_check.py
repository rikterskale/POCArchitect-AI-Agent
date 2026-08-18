import importlib.util
import io
from pathlib import Path

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
