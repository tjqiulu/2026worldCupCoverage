"""E2E tests for PWA (Progressive Web App) features (Plan 014)."""
import json
from pathlib import Path

import pytest
from playwright.sync_api import Page


class TestPwaManifest:
    def test_manifest_accessible(self, page: Page):
        """G1: /static/manifest.json is accessible and valid JSON."""
        resp = page.request.get("http://127.0.0.1:8766/static/manifest.json")
        assert resp.ok, f"Manifest not accessible: {resp.status}"
        manifest = resp.json()
        assert "name" in manifest
        assert "icons" in manifest
        assert "start_url" in manifest
        assert "display" in manifest

    def test_manifest_display_standalone(self, page: Page):
        """G3: manifest has display: 'standalone' for fullscreen."""
        resp = page.request.get("http://127.0.0.1:8766/static/manifest.json")
        manifest = resp.json()
        assert manifest.get("display") == "standalone"

    def test_manifest_has_required_icons(self, page: Page):
        """G4: manifest has at least 192 + 512 icon entries."""
        resp = page.request.get("http://127.0.0.1:8766/static/manifest.json")
        manifest = resp.json()
        icons = manifest.get("icons", [])
        sizes = [icon.get("sizes") for icon in icons]
        # At least one 192x192 and one 512x512
        assert any("192" in s for s in sizes if s), f"No 192x192 icon: {sizes}"
        assert any("512" in s for s in sizes if s), f"No 512x512 icon: {s}"

    def test_manifest_has_shortcuts(self, page: Page):
        """Optional: shortcuts to Matches/Bracket views."""
        resp = page.request.get("http://127.0.0.1:8766/static/manifest.json")
        manifest = resp.json()
        shortcuts = manifest.get("shortcuts", [])
        if shortcuts:  # optional but nice-to-have
            names = [s.get("short_name") for s in shortcuts]
            assert any("Matches" in n or "赛程" in n for n in names if n)


class TestPwaIcons:
    def test_icon_svg_accessible(self, page: Page):
        """G4: /static/img/icon.svg is accessible."""
        resp = page.request.get("http://127.0.0.1:8766/static/img/icon.svg")
        assert resp.ok
        # Verify it's an SVG
        body = resp.text()
        assert "svg" in body[:200].lower()

    def test_icon_192_png_exists(self, page: Page):
        """G4: 192x192 PNG exists."""
        path = Path("/home/lqiu/.openclaw/workspace/2026worldCupCoverage/src/static/img/icon-192.png")
        assert path.is_file()
        assert path.stat().st_size > 1000, f"Icon too small: {path.stat().st_size} bytes"

    def test_icon_512_png_exists(self, page: Page):
        """G4: 512x512 PNG exists."""
        path = Path("/home/lqiu/.openclaw/workspace/2026worldCupCoverage/src/static/img/icon-512.png")
        assert path.is_file()
        assert path.stat().st_size > 5000, f"Icon too small: {path.stat().st_size} bytes"


class TestPwaServiceWorker:
    def test_sw_file_accessible(self, page: Page):
        """G2: /static/sw.js is accessible."""
        resp = page.request.get("http://127.0.0.1:8766/static/sw.js")
        assert resp.ok
        body = resp.text()
        assert "addEventListener" in body
        assert "fetch" in body

    def test_sw_registration(self, page: Page):
        """G2: SW registers successfully in the browser.

        Note: SW is registered at /static/sw.js with scope /static/.
        navigator.serviceWorker.getRegistration() (singular, no args) only
        returns the registration that *controls* the current page; since the
        page is at / and the SW scope is /static/, we use getRegistrations()
        (plural) to find any registered SW.
        """
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)  # give SW time to register + activate
        state = page.evaluate("""async () => {
            if (!('serviceWorker' in navigator)) return {hasReg: false, err: 'no SW support'};
            const regs = await navigator.serviceWorker.getRegistrations();
            return {
                hasReg: regs.length > 0,
                count: regs.length,
                scopes: regs.map(r => r.scope),
                anyActive: regs.some(r => r.active || r.installing || r.waiting),
            };
        }""")
        assert state["hasReg"], f"SW not registered: {state}"


class TestPwaHtml:
    def test_manifest_link_in_html(self, page: Page):
        """G3: HTML has <link rel=manifest>."""
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        manifest_href = page.locator('link[rel="manifest"]').get_attribute("href")
        assert manifest_href is not None, "No manifest link in HTML"
        assert "manifest.json" in manifest_href

    def test_theme_color_in_html(self, page: Page):
        """G3: HTML has theme-color meta."""
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        theme = page.locator('meta[name="theme-color"]').get_attribute("content")
        assert theme is not None and theme.startswith("#"), f"Bad theme color: {theme}"

    def test_apple_touch_icon_in_html(self, page: Page):
        """G3: HTML has apple-touch-icon (for iOS)."""
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        icon = page.locator('link[rel="apple-touch-icon"]').get_attribute("href")
        assert icon is not None


class TestPwaInstall:
    def test_install_button_in_html(self, page: Page):
        """G7: HTML has hidden install button."""
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        btn = page.locator("#install-pwa-btn")
        assert btn.count() == 1
        # Initially hidden (beforeinstallprompt not yet fired in test)
        hidden = btn.get_attribute("hidden")
        assert hidden is not None, "Install button should be hidden initially"

    def test_no_console_errors_on_load(self, page: Page):
        """G8: No console errors when loading the page (PWA init shouldn't error)."""
        errors = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        # Filter out expected noise (flag-icons CDN, etc.)
        real_errors = [e for e in errors if "flag-icons" not in e and "favicon" not in e.lower()]
        assert len(real_errors) == 0, f"Console errors: {real_errors}"


class TestPwaVisual:
    def test_pwa_view_screenshot(self, page: Page):
        """Save screenshot of the page for visual review."""
        page.goto("http://127.0.0.1:8766", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        path = page.screenshot(path="tests/e2e/screenshots/pwa_view.png", full_page=True)
        assert path
