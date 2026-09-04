import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path

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
        assert page.get_by_role("button", name="Copy Markdown").is_visible()
        with page.expect_download() as download_info:
            page.locator("#download-report").click()
        downloaded = Path(download_info.value.path()).read_text(encoding="utf-8")
        assert "# POCArchitect Demo Report" in downloaded

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

        page.reload()
        page.locator("#connection-status").get_by_text("Ready").wait_for()
        assert page.evaluate("sessionStorage.getItem('pocarchitect.activeJob')") is None
        page.locator("#tab-reports").click()
        page.locator("#report-list button").first.wait_for()
        page.locator("#report-list button").first.click()
        page.locator("#library-report:not(.is-hidden)").wait_for()
        page.locator("#library-report-body").get_by_text(
            "POCArchitect Demo Report", exact=False
        ).wait_for()
        assert (
            "POCArchitect Demo Report"
            in page.locator("#library-report-body").text_content()
        )
        browser.close()


def test_browser_connection_interruption_and_retry(tmp_path, monkeypatch):
    with live_gui(tmp_path, monkeypatch) as launch_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/api/bootstrap", lambda route: route.abort())
        page.goto(launch_url)

        banner = page.locator("#connection-banner")
        banner.get_by_text("Connection interrupted.").wait_for()
        assert banner.get_by_role("button", name="Retry connection").is_visible()

        page.unroute("**/api/bootstrap")
        banner.get_by_role("button", name="Retry connection").click()
        page.locator("#connection-status").get_by_text("Ready").wait_for()
        assert banner.is_hidden()
        browser.close()


def test_browser_blocks_unconfigured_provider(tmp_path, monkeypatch):
    for variable in ("XAI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(variable, raising=False)

    with live_gui(tmp_path, monkeypatch) as launch_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(launch_url)
        page.locator("#connection-status").get_by_text("Ready").wait_for()

        page.locator("#provider-readiness-name").get_by_text(
            "needs configuration", exact=False
        ).wait_for()
        page.locator("#source").fill("https://example.com/advisory")
        page.locator("#prepare-button").click()
        page.locator("#review-content:not(.is-hidden)").wait_for()
        page.locator("#approval").check()

        assert page.locator("#run-button").is_disabled()
        assert page.get_by_role("button", name="Copy setup command").is_visible()
        browser.close()
