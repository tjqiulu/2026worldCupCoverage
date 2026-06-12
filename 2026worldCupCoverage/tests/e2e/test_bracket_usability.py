"""E2E tests for bracket usability (tab switching, refresh, today button)."""
from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page

from conftest import save_screenshot


class TestTabSwitching:
    def test_bracket_is_default(self, page: Page):
        """Bracket view should be visible by default (per Plan 003)."""
        bracket_view = page.locator("#bracket-view")
        matches_view = page.locator("#matches-view")
        assert "active" in (bracket_view.get_attribute("class") or "")

    def test_switch_to_matches(self, page: Page):
        """Click '赛程' tab → matches view should become active."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)  # let CSS update
        matches_view = page.locator("#matches-view")
        assert "active" in (matches_view.get_attribute("class") or "")

    def test_switch_back_to_bracket(self, page: Page):
        """Click '对阵' tab → bracket view should become active."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(200)
        page.click('button[data-tab="bracket"]')
        page.wait_for_timeout(200)
        bracket_view = page.locator("#bracket-view")
        assert "active" in (bracket_view.get_attribute("class") or "")

    def test_screenshot_matches_view(self, page: Page):
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(500)
        path = save_screenshot(page, "matches_view")
        print(f"\n[INFO] Matches screenshot: {path}")


class TestTodayButton:
    def test_today_button_switches_to_matches(self, page: Page):
        """Click '今天' → should switch to matches view and scroll to today."""
        # Start in bracket view
        page.click("#today-btn")
        page.wait_for_timeout(500)
        matches_view = page.locator("#matches-view")
        assert "active" in (matches_view.get_attribute("class") or "")


class TestRefreshButton:
    def test_refresh_button_works(self, page: Page):
        """Click '刷新' → should call /api/refresh and reload matches."""
        # Spy on the /api/refresh call
        requests_made = []
        page.on("request", lambda req: requests_made.append(req.url) if "api/refresh" in req.url else None)

        page.click("#refresh-btn")
        # Wait for the refresh to complete (button text changes back to original)
        page.wait_for_function(
            '() => document.getElementById("refresh-btn").textContent.includes("刷新") && !document.getElementById("refresh-btn").disabled',
            timeout=10_000,
        )
        # Verify the API was called
        assert any("api/refresh" in u for u in requests_made), (
            f"Refresh button didn't call /api/refresh. Requests: {requests_made}"
        )


class TestPageLoad:
    def test_no_console_errors(self, page: Page):
        """Page should load without JavaScript console errors."""
        # Re-navigate to capture errors from start
        errors: list[str] = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.reload(wait_until="networkidle")
        # Filter out known false positives (e.g., flag-icons CDN might 404 in some envs)
        real_errors = [e for e in errors if "flag-icons" not in e]
        assert len(real_errors) == 0, f"Console errors: {real_errors}"

    def test_load_time_under_5s(self, page: Page):
        """Page should load in under 5 seconds (relaxed from 2s for e2e)."""
        start = time.time()
        page.goto("http://127.0.0.1:8766", wait_until="networkidle")
        page.wait_for_selector(".bracket-card", timeout=10_000)
        elapsed = time.time() - start
        assert elapsed < 5, f"Page load took {elapsed:.2f}s (>5s limit)"


class TestBracketInteraction:
    def test_bracket_card_has_title(self, page: Page):
        """Each bracket card should have a title attribute with full match info."""
        first_card = page.locator(".bracket-card.r32").first
        title = first_card.get_attribute("title")
        assert title is not None and "vs" in title, (
            f"First R32 card has no title or 'vs': {title!r}"
        )

    def test_flag_icons_loaded(self, page: Page):
        """Real country cards should have flag icons rendered."""
        # Find a known real country (Brazil should be in the bracket)
        brazil_card = page.locator('.team-name:has-text("巴西")').first
        if brazil_card.count() == 0:
            pytest.skip("Brazil not visible in current view")
        flag = brazil_card.locator(".fi").first
        assert flag.count() > 0, "Brazil card missing flag icon"
        flag_class = flag.get_attribute("class") or ""
        assert "fi-br" in flag_class, f"Flag class missing 'fi-br': {flag_class!r}"
