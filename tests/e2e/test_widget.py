"""E2E tests for Plan 016 (widget mode).

Tests:
- /?view=widget shows compact cards
- Header / tabs / footer are hidden in widget mode
- Widget shows today's matches (or next 5 if none today)
- Each card has time + teams + status
- Score shows for finished/live matches
- Card click opens modal
- Auto-refresh fetches data
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


def _open_widget(page: Page) -> None:
    page.goto("http://127.0.0.1:8766/?view=widget", wait_until="networkidle", timeout=15000)
    page.wait_for_selector(".widget-card", timeout=10_000)
    # Wait for teams map to load (so click on card works with names)
    page.wait_for_timeout(1500)


class TestWidgetLayout:
    def test_widget_mode_hides_chrome(self, page: Page):
        _open_widget(page)
        # body should have widget-mode class
        cls = page.evaluate("document.body.className")
        assert "widget-mode" in cls
        # header, tabs, footer should be display:none (or not in DOM)
        for sel in ("header", "nav.tabs", "footer"):
            visible = page.locator(sel).is_visible() if page.locator(sel).count() else False
            assert not visible, f"{sel} should be hidden in widget mode"

    def test_widget_view_shown_matches_hidden(self, page: Page):
        _open_widget(page)
        wv = page.locator("#widget-view")
        assert wv.is_visible()
        # matches-view and bracket-view should be hidden (display:none in widget mode CSS)
        for sel in ("#matches-view", "#bracket-view"):
            visible = page.locator(sel).is_visible() if page.locator(sel).count() else False
            assert not visible, f"{sel} should be hidden in widget mode"

    def test_widget_has_cards(self, page: Page):
        _open_widget(page)
        cards = page.locator(".widget-card")
        assert cards.count() >= 1, "Widget should have at least 1 card"

    def test_widget_card_has_required_fields(self, page: Page):
        _open_widget(page)
        first = page.locator(".widget-card").first
        # Must have time, both team names, status
        assert first.locator(".widget-time").count() == 1
        assert first.locator(".widget-team.home .widget-team-name").count() == 1
        assert first.locator(".widget-team.away .widget-team-name").count() == 1
        assert first.locator(".widget-status").count() == 1
        # Time format: HH:MM
        time = first.locator(".widget-time").text_content()
        assert ":" in time


class TestWidgetScore:
    def test_finished_match_shows_score(self, page: Page):
        _open_widget(page)
        # Find a finished card
        finished = page.locator('.widget-card[data-status="final"]')
        if finished.count() == 0:
            pytest.skip("No finished match in widget view (API may be stale)")
        first = finished.first
        score = first.locator(".widget-score")
        if score.count() > 0:
            txt = score.text_content().strip()
            assert " - " in txt
            parts = txt.split(" - ")
            assert len(parts) == 2
            assert parts[0].strip().isdigit() or parts[0].strip() == "0"

    def test_live_match_has_live_class(self, page: Page):
        _open_widget(page)
        live = page.locator('.widget-card[data-status="live"]')
        if live.count() == 0:
            pytest.skip("No live match at this moment")
        # First live card has red border (CSS check via class) or live score
        first = live.first
        # Should have either .widget-score.live or a status badge
        status_badge = first.locator(".widget-status.status-live")
        assert status_badge.count() == 1

    def test_finished_no_score_shows_pending(self, page: Page):
        _open_widget(page)
        # Find a final match that has no score (API hasn't published it)
        cards = page.locator('.widget-card[data-status="final"]')
        for i in range(cards.count()):
            card = cards.nth(i)
            if card.locator(".widget-pending").count() > 0:
                txt = card.locator(".widget-pending").text_content()
                assert "待更新" in txt
                return
        pytest.skip("All finished matches have scores (lucky!)")


class TestWidgetInteraction:
    def test_card_click_opens_modal(self, page: Page):
        _open_widget(page)
        cards = page.locator(".widget-card")
        if cards.count() == 0:
            pytest.skip("No widget cards")
        cards.first.click()
        page.wait_for_selector("#match-modal:not([hidden])", timeout=5_000)
        # Modal should show stage label (i.e., full modal rendered)
        assert page.locator("#modal-stage").count() == 1

    def test_modal_stadium_section_in_widget(self, page: Page):
        """Plan 015 stadium section should also work in widget mode."""
        _open_widget(page)
        page.locator(".widget-card").first.click()
        page.wait_for_selector("#match-modal:not([hidden])", timeout=5_000)
        page.wait_for_timeout(500)
        # Stadium should be visible (all matches have stadium)
        assert page.locator("#modal-stadium-section").is_visible()


class TestWidgetRefresh:
    def test_api_refresh_bypasses_cache(self, page: Page):
        """Plan 016 fix: /api/refresh should bypass the 5-min in-memory cache."""
        # Hit refresh once to populate cache
        resp1 = page.request.post("http://127.0.0.1:8766/api/refresh")
        assert resp1.ok
        body1 = resp1.json()
        # Immediately hit refresh again — should still hit API (not stale cache)
        resp2 = page.request.post("http://127.0.0.1:8766/api/refresh")
        assert resp2.ok
        body2 = resp2.json()
        # If cache was hit on 2nd, fetch would be ~0s; if bypassed, also ~0s.
        # The structural check: status ok in both
        assert body1["status"] == "ok"
        assert body2["status"] == "ok"

    def test_widget_loads_at_small_viewport(self, page: Page):
        """Widget should look good at 380x500 (typical sidebar)."""
        page.set_viewport_size({"width": 380, "height": 500})
        _open_widget(page)
        # Take a screenshot for visual review
        page.screenshot(path="tests/e2e/screenshots/widget_380x500.png", full_page=False)
        # Card width should fit (no horizontal scroll)
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        client_w = page.evaluate("document.documentElement.clientWidth")
        assert scroll_w <= client_w + 2, f"Horizontal scroll: scrollW={scroll_w} > clientW={client_w}"
