#!/usr/bin/env python3
"""Desktop launcher: starts Flask + opens browser in fullscreen, cleans up on close.

Usage:
    python3 bin/launch.py                  # start Flask + open browser kiosk
    python3 bin/launch.py --no-browser     # just start Flask (debug / CI)
    python3 bin/launch.py --url http://... # custom URL
    python3 bin/launch.py --browser firefox # pick specific browser

Behaviour:
    1. Starts Flask in background (subprocess)
    2. Waits for HTTP health check (max 30s)
    3. Detects installed browser (chromium / google-chrome / firefox)
    4. Launches browser in --kiosk mode (fullscreen, no chrome)
    5. Blocks until browser closes
    6. Sends SIGTERM to Flask
    7. Exits

Ctrl+C at any point: cleans up both processes and exits.
"""
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "http://127.0.0.1:8766"
DEFAULT_HEALTH_TIMEOUT = 30  # seconds to wait for Flask
BROWSER_POLL_INTERVAL = 0.5  # seconds between browser-alive checks

# Browser detection: (executable_name, [kiosk_args])
BROWSERS = [
    ("chromium-browser", ["--kiosk", "--noerrdialogs", "--disable-infobars",
                           "--disable-features=Translate", "--no-first-run"]),
    ("chromium", ["--kiosk", "--noerrdialogs", "--disable-infobars",
                  "--disable-features=Translate", "--no-first-run"]),
    ("google-chrome", ["--kiosk", "--noerrdialogs", "--disable-infobars",
                       "--disable-features=Translate", "--no-first-run"]),
    ("chrome", ["--kiosk", "--noerrdialogs", "--disable-infobars"]),
    ("firefox", ["--kiosk", "--new-instance"]),
    ("google-chrome-stable", ["--kiosk", "--noerrdialogs", "--disable-infobars"]),
]


def find_browser(prefer: Optional[str] = None) -> tuple[Optional[str], list[str]]:
    """Find an installed browser. Returns (path, args) or (None, [])."""
    # If user specified a browser, use that
    if prefer:
        path = shutil.which(prefer)
        if path:
            # Look up default args
            for name, args in BROWSERS:
                if name == prefer or prefer in name:
                    return path, args
            return path, ["--kiosk"]  # fallback kiosk args
        print(f"Warning: requested browser '{prefer}' not found")

    for name, args in BROWSERS:
        path = shutil.which(name)
        if path:
            return path, args
    return None, []


def wait_for_http(url: str, timeout: int = DEFAULT_HEALTH_TIMEOUT) -> bool:
    """Wait until HTTP server responds, or timeout. Returns True if ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    return False


def start_flask(project_root: Path) -> subprocess.Popen:
    """Start the Flask app as a subprocess. Returns the Popen object."""
    return subprocess.Popen(
        ["python3", "src/app.py"],
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # Put flask in its own process group so we can SIGTERM it
        preexec_fn=os.setsid if sys.platform != "win32" else None,
    )


def start_browser(browser_path: str, browser_args: list[str], url: str) -> subprocess.Popen:
    """Start the browser pointing at url. Returns the Popen object."""
    return subprocess.Popen(
        [browser_path] + browser_args + [url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid if sys.platform != "win32" else None,
    )


def terminate_process(proc: subprocess.Popen, name: str = "process") -> None:
    """Send SIGTERM (or terminate on Windows) and wait briefly."""
    if proc.poll() is not None:
        return  # already exited
    try:
        if sys.platform == "win32":
            proc.terminate()
        else:
            # Send SIGTERM to the whole process group
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                proc.terminate()
    except Exception as e:
        print(f"Warning: failed to terminate {name}: {e}")
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print(f"Warning: {name} did not exit, sending SIGKILL")
        try:
            if sys.platform == "win32":
                proc.kill()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch WC2026 Coverage app in desktop fullscreen mode"
    )
    parser.add_argument("--url", default=DEFAULT_URL,
                        help=f"URL to open (default: {DEFAULT_URL})")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't open browser, just run Flask (for debug / CI)")
    parser.add_argument("--browser", default=None,
                        help="Specific browser to use (e.g., chromium, firefox)")
    parser.add_argument("--health-timeout", type=int, default=DEFAULT_HEALTH_TIMEOUT,
                        help=f"Seconds to wait for Flask (default: {DEFAULT_HEALTH_TIMEOUT})")
    args = parser.parse_args()

    flask_proc: Optional[subprocess.Popen] = None
    browser_proc: Optional[subprocess.Popen] = None

    def cleanup(sig: int = 0, frame=None) -> None:
        """Cleanup both processes. Safe to call multiple times."""
        if browser_proc is not None:
            terminate_process(browser_proc, "browser")
        if flask_proc is not None:
            terminate_process(flask_proc, "flask")
        if sig:
            print(f"\nReceived signal {sig}, cleaning up...")
            sys.exit(0)

    # Register signal handlers (Unix only)
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, lambda s, f: cleanup(s, f))
        signal.signal(signal.SIGTERM, lambda s, f: cleanup(s, f))

    # 1. Start Flask
    print(f"[launcher] Starting Flask at {args.url}...")
    flask_proc = start_flask(PROJECT_ROOT)

    # 2. Wait for Flask ready
    print(f"[launcher] Waiting for Flask (timeout: {args.health_timeout}s)...")
    if not wait_for_http(args.url, timeout=args.health_timeout):
        print(f"[launcher] ERROR: Flask did not start within {args.health_timeout}s")
        cleanup()
        return 1
    print(f"[launcher] Flask ready at {args.url}")

    # 3. Open browser (unless --no-browser)
    if args.no_browser:
        print("[launcher] --no-browser mode: Flask running. Press Ctrl+C to stop.")
        try:
            flask_proc.wait()
        except KeyboardInterrupt:
            cleanup()
        return 0

    # 4. Find and launch browser
    browser_path, browser_args = find_browser(args.browser)
    if not browser_path:
        print("[launcher] ERROR: No supported browser found.")
        print("  Install one of: chromium-browser, chromium, google-chrome, firefox")
        print("  Or use --no-browser to run without GUI")
        print("  Flask is still running at {}. Press Ctrl+C to stop.".format(args.url))
        try:
            flask_proc.wait()
        except KeyboardInterrupt:
            cleanup()
        return 1

    print(f"[launcher] Launching {os.path.basename(browser_path)} in kiosk mode...")
    browser_proc = start_browser(browser_path, browser_args, args.url)

    # 5. Wait for browser to close
    print("[launcher] Browser launched. Close it to stop the app.")
    try:
        while True:
            ret = browser_proc.poll()
            if ret is not None:
                print(f"[launcher] Browser exited with code {ret}")
                break
            time.sleep(BROWSER_POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n[launcher] Interrupted, cleaning up...")

    # 6. Cleanup
    cleanup()
    print("[launcher] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
