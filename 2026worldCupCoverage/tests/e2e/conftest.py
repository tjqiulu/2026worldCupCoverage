"""E2E test fixtures: Flask server + Playwright browser."""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, sync_playwright

# Project root (so Flask can be started from the right cwd)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Screenshots dir (gitignored)
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Test server URL (must match app.py)
SERVER_URL = "http://127.0.0.1:8766"

# Skip e2e tests if PLAYWRIGHT_BROWSERS_PATH is not set (or browser not installed)
pytestmark = pytest.mark.e2e


def _flask_already_running() -> bool:
    """Check if Flask is already running (e.g., user started it manually)."""
    import urllib.request
    try:
        urllib.request.urlopen(SERVER_URL, timeout=1)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def flask_server() -> str:
    """Start Flask in subprocess (or reuse if already running). Return base URL."""
    if _flask_already_running():
        yield SERVER_URL
        return
    env = os.environ.copy()
    # Disable Flask reloader (don't spawn child processes)
    env["FLASK_RUN_FROM_CLI"] = "false"
    proc = subprocess.Popen(
        ["python3", "src/app.py"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for server to be ready
    import urllib.request
    for _ in range(30):  # 30s timeout
        try:
            urllib.request.urlopen(SERVER_URL, timeout=1)
            break
        except Exception:
            time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError(f"Flask did not start within 30s at {SERVER_URL}")
    try:
        yield SERVER_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def browser() -> Browser:
    """Launch headless Chromium once per test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def page(browser: Browser, flask_server: str, request: pytest.FixtureRequest) -> Page:
    """Fresh page per test, with screenshot on failure."""
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = context.new_page()

    # Capture console errors for assertions
    console_errors: list[str] = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

    # Navigate
    page.goto(flask_server, wait_until="networkidle")
    # Wait for data load: bracket view is default, wait for visible bracket cards
    # (Both views exist in DOM, but only bracket-view is .active so its cards are visible)
    page.wait_for_selector("#bracket-view.active .bracket-card", timeout=10_000)

    yield page

    # Screenshot on failure
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        try:
            page.screenshot(path=str(SCREENSHOTS_DIR / f"FAIL_{request.node.name}.png"), full_page=True)
        except Exception:
            pass

    context.close()


def save_screenshot(page: Page, name: str) -> Path:
    """Save screenshot to tests/e2e/screenshots/."""
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return path
