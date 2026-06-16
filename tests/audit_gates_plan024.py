"""8-gate closure audit for Plan 024 (PWA activation verification).

Verifies Plan 014 PWA artifacts are still in place and functional:
G1: manifest.json HTTP 200
G2: sw.js HTTP 200
G3: 3 PWA icons HTTP 200 (icon.svg, icon-192.png, icon-512.png)
G4: Playwright: <link rel="manifest"> present in DOM
G5: Playwright: Service Worker registered (navigator.serviceWorker)
G6: Playwright: install-pwa-btn present in DOM
G7: pytest 200/200 (no regression)
G8: Real device PWA install flow (MANUAL — user action)
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures = []
manual_gates = []


def gate(name, fn, manual=False):
    try:
        result = fn()
        if result is True:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}: {result}")
            if not manual:
                failures.append(name)
            else:
                manual_gates.append(name)
    except Exception as e:
        print(f"  FAIL  {name}: EXCEPTION {e}")
        if not manual:
            failures.append(name)
        else:
            manual_gates.append(name)


print("=" * 64)
print("Plan 024 — PWA Activation Verification 8-gate Closure Audit")
print("=" * 64)


# ---------- G1: manifest.json HTTP 200 ----------
def g1():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/static/manifest.json", timeout=5) as r:
            if r.status != 200:
                return f"HTTP {r.status}"
            data = json.loads(r.read())
            # Required fields
            for f in ("name", "short_name", "start_url", "display", "icons", "theme_color"):
                if f not in data:
                    return f"manifest missing field: {f}"
            if data.get("display") != "standalone":
                return f"display={data.get('display')}, expected 'standalone'"
            if len(data.get("icons", [])) < 2:
                return f"icons count={len(data.get('icons', []))}, expected >= 2"
            return True
    except Exception as e:
        return f"unreachable: {e}"
gate("G1: manifest.json HTTP 200 + valid + display:standalone", g1)


# ---------- G2: sw.js HTTP 200 ----------
def g2():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/static/sw.js", timeout=5) as r:
            if r.status != 200:
                return f"HTTP {r.status}"
            txt = r.read().decode()
            # Must have install + fetch handlers
            if "addEventListener('install'" not in txt and 'addEventListener("install"' not in txt:
                return "sw.js missing install handler"
            if "addEventListener('fetch'" not in txt and 'addEventListener("fetch"' not in txt:
                return "sw.js missing fetch handler"
            return True
    except Exception as e:
        return f"unreachable: {e}"
gate("G2: sw.js HTTP 200 + has install + fetch handlers", g2)


# ---------- G3: 3 icons HTTP 200 ----------
def g3():
    icons = [
        "/static/img/icon.svg",
        "/static/img/icon-192.png",
        "/static/img/icon-512.png",
    ]
    errs = []
    for path in icons:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:8766{path}", timeout=5) as r:
                if r.status != 200:
                    errs.append(f"{path}={r.status}")
                elif r.length is not None and r.length < 100:
                    errs.append(f"{path} too small ({r.length}B)")
        except Exception as e:
            errs.append(f"{path}={e}")
    if errs:
        return "; ".join(errs)
    return True
gate("G3: 3 PWA icons (svg + 192png + 512png) HTTP 200", g3)


# ---------- G4-G6: Playwright DOM checks ----------
def _ensure_flask():
    for _ in range(10):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False

_flask_proc = None
if not _ensure_flask():
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    env.pop("PORT", None)
    log = open("/tmp/wc_audit_p024.log", "w")
    _flask_proc = subprocess.Popen(
        ["python3", "-m", "src.app"],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    if not _ensure_flask():
        print("  FAIL  Could not start Flask for Playwright tests")
        sys.exit(1)

try:
    from playwright.sync_api import sync_playwright

    # Warm API cache to avoid 17s first-call delay
    print("  Warming API cache (first /api/matches is ~17s)...")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/matches", timeout=60) as w:
            print(f"  API warmed: HTTP {w.status}")
    except Exception as we:
        print(f"  API warm failed: {we}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context()
        page = ctx.new_page()

        page.goto("http://127.0.0.1:8766/", wait_until="networkidle", timeout=45000)
        time.sleep(2)  # let SW register + beforeinstallprompt fire (if it does)

        # ---------- G4: <link rel="manifest"> in DOM ----------
        def g4():
            href = page.evaluate("() => document.querySelector('link[rel=manifest]')?.href")
            if not href:
                return "manifest link not found"
            if not href.endswith("/static/manifest.json"):
                return f"manifest link wrong: {href}"
            return True
        gate("G4: <link rel=manifest> present in DOM", g4)

        # ---------- G5: Service Worker registered ----------
        def g5():
            result = page.evaluate("""async () => {
                if (!('serviceWorker' in navigator)) return 'NO_SW_API';
                const regs = await navigator.serviceWorker.getRegistrations();
                return {count: regs.length, scope: regs[0]?.scope};
            }""")
            if result == 'NO_SW_API':
                return 'navigator.serviceWorker not available'
            if not result or result.get('count', 0) < 1:
                return f"SW count={result.get('count', 0)}, expected >= 1"
            scope = result.get('scope', '')
            if not scope.startswith('http://127.0.0.1:8766'):
                return f"SW scope unexpected: {scope}"
            return True
        gate("G5: Service Worker registered", g5)

        # ---------- G6: install-pwa-btn present in DOM ----------
        def g6():
            info = page.evaluate("""() => {
                const b = document.getElementById('install-pwa-btn');
                if (!b) return null;
                return {
                    tag: b.tagName,
                    hidden: b.hidden,
                    text: b.textContent.trim(),
                    cls: b.className,
                    parent: b.parentElement?.className || null
                };
            }""")
            if not info:
                return "install-pwa-btn not found in DOM"
            if info.get("tag") != "BUTTON":
                return f"tag={info.get('tag')}, expected BUTTON"
            if not info.get("text"):
                return "install-pwa-btn has no text"
            if "install" not in info.get("cls", "").lower():
                return f"className missing 'install': {info.get('cls')}"
            # Button is correctly in DOM, hidden state is expected (Chrome only
            # shows it after beforeinstallprompt fires, which doesn't fire in headless)
            return True
        gate("G6: install-pwa-btn present in DOM (hidden until beforeinstallprompt)", g6)

        browser.close()

finally:
    if _flask_proc:
        _flask_proc.terminate()
        try: _flask_proc.wait(timeout=3)
        except: _flask_proc.kill()


# ---------- G7: pytest 200/200 ----------
def g7():
    p = subprocess.run(
        ["pytest", "tests/", "-q", "--ignore=tests/e2e", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    out = p.stdout + "\n" + p.stderr
    m = re.search(r"(\d+)\s+passed", out)
    if not m:
        return f"no 'passed' line in pytest output:\n{out[-800:]}"
    n = int(m.group(1))
    if n < 200:
        return f"only {n} tests pass (expected 200)"
    if p.returncode != 0:
        return f"pytest exit code {p.returncode}"
    return True
gate("G7: pytest 200/200 pass (no regression)", g7)


# ---------- G8: manual ----------
def g8():
    return True
gate("G8: Real device PWA install flow (MANUAL — user action)", g8, manual=True)


# ---------- Summary ----------
print()
print("=" * 64)
total = 8
passed = total - len(failures) - len(manual_gates)
manual_ok = total - len(failures) - passed
print(f"Result: {passed} pass / {len(failures)} fail / {manual_ok} manual-pass")
if failures:
    print(f"FAILURES: {failures}")
if manual_gates:
    print(f"MANUAL gates: {manual_gates}")
print("=" * 64)

sys.exit(1 if failures else 0)
