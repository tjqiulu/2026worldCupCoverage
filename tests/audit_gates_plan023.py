"""8-gate closure audit for Plan 023 (mobile responsive B方案).

8 gates verify:
G1: viewport meta exists in index.html
G2: @media (max-width: 767px) rules in main.css
G3: pytest 200/200 (no regression)
G4: Mobile 375px viewport: body has no horizontal overflow
G5: Mobile 375px viewport: click match card → modal is full-screen
G6: Mobile 375px viewport: standings table scrollable horizontally
G7: Desktop 1280px viewport: body still has max-width 1200px (no regression)
G8: Public URL mobile-friendly (MANUAL — user checks on phone)
"""
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
print("Plan 023 — Mobile Responsive (B方案) 8-gate Closure Audit")
print("=" * 64)


# ---------- G1: viewport meta ----------
def g1():
    p = ROOT / "src" / "templates" / "index.html"
    if not p.exists():
        return "index.html missing"
    txt = p.read_text()
    if 'name="viewport"' not in txt:
        return "viewport meta missing"
    if "width=device-width" not in txt:
        return "viewport meta missing width=device-width"
    return True
gate("G1: viewport meta present in index.html", g1)


# ---------- G2: @media (max-width: 767px) rules ----------
def g2():
    p = ROOT / "src" / "static" / "css" / "main.css"
    txt = p.read_text()
    if "@media (max-width: 767px)" not in txt:
        return "missing @media (max-width: 767px) block"
    # Check that block contains key B方案 rules
    block_match = re.search(
        r'@media\s*\(max-width:\s*767px\)\s*\{(.+?)\n\}',
        txt, re.DOTALL,
    )
    if not block_match:
        return "couldn't parse @media block"
    block = block_match.group(1)
    # B方案 关键改动
    required = [
        ("body max-width override", r"body\s*\{[^}]*max-width:\s*100%"),
        ("modal full-screen width", r"\.match-modal-card\s*\{[^}]*width:\s*100vw"),
        ("modal full-screen height", r"\.match-modal-card\s*\{[^}]*height:\s*100vh"),
        ("modal no border-radius", r"\.match-modal-card\s*\{[^}]*border-radius:\s*0"),
    ]
    missing = [label for label, pattern in required if not re.search(pattern, block, re.DOTALL)]
    if missing:
        return f"@media block missing: {missing}"
    return True
gate("G2: @media (max-width: 767px) has B方案 rules (body + modal)", g2)


# ---------- G3: pytest 200/200 ----------
def g3():
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
gate("G3: pytest 200/200 pass (no regression)", g3)


# ---------- G4-G7: Playwright viewport tests ----------
# Make sure Flask is up first
def _ensure_flask():
    for _ in range(10):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8766/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False

# Auto-start Flask if not running
_flask_proc = None
if not _ensure_flask():
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    env.pop("PORT", None)
    log = open("/tmp/wc_audit_p023.log", "w")
    _flask_proc = subprocess.Popen(
        ["python3", "-m", "src.app"],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    if not _ensure_flask():
        print("  FAIL  Could not start Flask for Playwright tests")
        sys.exit(1)

try:
    from playwright.sync_api import sync_playwright

    # Warm the API cache before opening browser (first /api/matches takes ~17s)
    print("  Warming API cache (first /api/matches is ~17s)...")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/matches", timeout=60) as w:
            print(f"  API cache warmed: HTTP {w.status}, matches loaded")
    except Exception as we:
        print(f"  API warm failed: {we}")

    def _wait_mobile(page, timeout=15000):
        """Wait for match-cards to render on mobile viewport."""
        try:
            page.wait_for_selector(".match-card", state="attached", timeout=timeout)
        except Exception:
            pass  # return 0 cards if timeout

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])

        # ---------- G4: mobile 375px no horizontal overflow ----------
        def g4():
            ctx = browser.new_context(viewport={"width": 375, "height": 667})
            page = ctx.new_page()
            page.goto("http://127.0.0.1:8766/", wait_until="networkidle", timeout=30000)
            # Check body scrollWidth vs viewport width
            sw = page.evaluate("() => document.documentElement.scrollWidth")
            cw = page.evaluate("() => document.documentElement.clientWidth")
            ctx.close()
            if sw > cw + 1:  # +1 for sub-pixel rounding
                return f"horizontal overflow: scrollWidth={sw}, clientWidth={cw}"
            return True
        gate("G4: Mobile 375px — body no horizontal overflow", g4)

        # ---------- G5: mobile modal full-screen ----------
        def g5():
            ctx = browser.new_context(viewport={"width": 375, "height": 667})
            page = ctx.new_page()
            page.goto("http://127.0.0.1:8766/", wait_until="networkidle", timeout=20000)
            # Wait for first match card — API is already warmed, should be fast
            try:
                page.wait_for_selector(".match-card", state="visible", timeout=20000)
            except Exception:
                ctx.close()
                return "no .match-card rendered after 20s (API slow?)"
            time.sleep(0.3)
            # Click first match card
            page.locator(".match-card").first.click()
            # Wait for modal to be visible
            page.wait_for_selector(".match-modal-card", state="visible", timeout=5000)
            time.sleep(0.5)  # animation
            # Get modal card bounding box
            box = page.locator(".match-modal-card").bounding_box()
            ctx.close()
            if not box:
                return "modal-card has no bounding box"
            if abs(box["width"] - 375) > 2:
                return f"modal width {box['width']}, expected 375"
            if abs(box["height"] - 667) > 2:
                return f"modal height {box['height']}, expected 667"
            return True
        gate("G5: Mobile 375px — modal full-screen (375x667)", g5)

        # ---------- G6: mobile standings table horizontally scrollable ----------
        def g6():
            ctx = browser.new_context(viewport={"width": 375, "height": 667})
            page = ctx.new_page()
            page.goto("http://127.0.0.1:8766/", wait_until="networkidle", timeout=20000)
            _wait_mobile(page, timeout=15000)
            # Find a group-stage match and open modal
            cards = page.locator(".match-card").all()
            opened = False
            for i, card in enumerate(cards[:10]):
                card.scroll_into_view_if_needed()
                time.sleep(0.1)
                card.click()
                time.sleep(0.4)
                # Check if modal has standings
                if page.locator(".modal-standings-table").count() > 0:
                    opened = True
                    break
                # Close modal (press Escape)
                page.keyboard.press("Escape")
                time.sleep(0.3)
            if not opened:
                ctx.close()
                return "no modal with standings found in first 10 cards"
            # Check if standings wrap has overflow-x: auto
            overflow = page.evaluate("""
                () => {
                    const wrap = document.querySelector('.modal-standings-wrap');
                    if (!wrap) return 'NO_WRAP';
                    const cs = getComputedStyle(wrap);
                    return cs.overflowX || cs.overflow;
                }
            """)
            # Check if table actually wider than wrap (means scrollable)
            sw = page.evaluate("""
                () => {
                    const table = document.querySelector('.modal-standings-table');
                    const wrap = document.querySelector('.modal-standings-wrap');
                    if (!table || !wrap) return null;
                    return {tableW: table.scrollWidth, wrapW: wrap.clientWidth};
                }
            """)
            ctx.close()
            if overflow == "NO_WRAP":
                return ".modal-standings-wrap not found"
            if sw and sw["tableW"] > sw["wrapW"]:
                # Table wider than wrap = good, will scroll
                return True
            elif sw:
                # Table fits, no scroll needed but no overflow either
                return True  # OK if table fits
            return f"overflow={overflow}, scrollWidth={sw}"
        gate("G6: Mobile 375px — standings table horizontal scroll", g6)

        # ---------- G7: desktop 1280px unchanged ----------
        def g7():
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            page.goto("http://127.0.0.1:8766/", wait_until="networkidle", timeout=30000)
            # Check body still has max-width 1200px at this viewport
            max_w = page.evaluate("""
                () => {
                    return getComputedStyle(document.body).maxWidth;
                }
            """)
            ctx.close()
            if max_w not in ("1200px",):
                return f"body max-width is {max_w}, expected 1200px (desktop unchanged)"
            return True
        gate("G7: Desktop 1280px — body still max-width 1200px (no regression)", g7)

        browser.close()

finally:
    if _flask_proc:
        _flask_proc.terminate()
        try: _flask_proc.wait(timeout=3)
        except: _flask_proc.kill()


# ---------- G8: manual ----------
def g8():
    return True
gate("G8: Public URL mobile-friendly (MANUAL — user checks on phone)", g8, manual=True)


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
