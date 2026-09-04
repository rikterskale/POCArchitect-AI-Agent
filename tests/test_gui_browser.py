import socket
import threading
import time
from contextlib import contextmanager

import uvicorn
from playwright.sync_api import sync_playwright

from pocarchitect.gui import GuiRuntime, create_app
from pocarchitect.service import AnalysisService


@contextmanager
def live_gui(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pocarchitect.gui.default_output_dir", lambda: tmp_path / "reports"
    )
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    token = "browser-test-session"
    runtime = GuiRuntime(AnalysisService())
    app = create_app(session_token=token, port=port, runtime=runtime)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.02)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("GUI test server did not start")
    try:
        yield f"http://127.0.0.1:{port}/?token={token}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_browser_form_validation_demo_recovery_and_report_library(
    tmp_path, monkeypatch
):
    with live_gui(tmp_path, monkeypatch) as launch_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(launch_url)
        page.locator("#connection-status").get_by_text("Ready").wait_for()

        page.locator("#prepare-button").click()
        assert page.locator("#source-error").text_content() == (
            "Enter a repository, package, image, or source URL."
        )
        assert page.locator("#source").evaluate(
            "element => element === document.activeElement"
        )

        page.locator("#run-demo").click()
        page.locator("#report-content:not(.is-hidden)").wait_for(timeout=15_000)
        assert "POCArchitect Demo Report" in page.locator("#report-body").text_content()
        assert (
            page.locator("#download-report").get_attribute("href").endswith("/download")
        )

        active_job = page.evaluate("sessionStorage.getItem('pocarchitect.activeJob')")
        assert active_job is None

        page.locator("#tab-reports").click()
        page.locator("#report-list button").first.wait_for()
        page.locator("#report-list button").first.click()
        page.locator("#library-report:not(.is-hidden)").wait_for()
        assert (
            "POCArchitect Demo Report"
            in page.locator("#library-report-body").text_content()
        )
        browser.close()
