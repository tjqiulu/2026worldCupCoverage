"""E2E tests for match detail modal (Plan 009)."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


class TestModalOpen:
    def test_click_match_in_matches_view_opens_modal(self, page: Page):
        """Click a group-stage match card (real countries) → modal opens."""
        # Switch to matches view
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        # Click first match in matches view
        first_card = page.locator('#matches-view .match-card').first
        first_card.click()
        page.wait_for_timeout(500)
        modal = page.locator('#match-modal')
        assert modal.get_attribute('hidden') is None, "Modal should be visible after click"

    def test_click_bracket_card_opens_modal(self, page: Page):
        """Click an R32 card (placeholders) → modal opens."""
        # Already in bracket view by default
        first_r32 = page.locator('.bracket-card.r32').first
        first_r32.click()
        page.wait_for_timeout(500)
        modal = page.locator('#match-modal')
        assert modal.get_attribute('hidden') is None

    def test_modal_hidden_initially(self, page: Page):
        """Modal should be hidden on page load."""
        modal = page.locator('#match-modal')
        assert modal.get_attribute('hidden') is not None


class TestModalContentRealCountry:
    """Verify modal shows correct info for a real country match."""

    @pytest.fixture
    def opened_modal(self, page: Page):
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        first_card = page.locator('#matches-view .match-card').first
        first_card.click()
        page.wait_for_timeout(500)
        return page

    def test_stage_label(self, opened_modal):
        stage = opened_modal.locator('#modal-stage').text_content()
        assert "小组赛" in stage
        assert "Group" in stage

    def test_date_format(self, opened_modal):
        date = opened_modal.locator('#modal-date').text_content()
        # Format: "X 月 Y 日 星期Z HH:MM（北京时间）"
        assert "月" in date and "日" in date and "北京时间" in date

    def test_home_team_has_flag(self, opened_modal):
        home = opened_modal.locator('#modal-home')
        flag = home.locator('.fi')
        assert flag.count() > 0, "Home team should have flag icon"
        flag_class = flag.get_attribute('class') or ""
        assert "fi-" in flag_class

    def test_home_team_has_bilingual_name(self, opened_modal):
        home = opened_modal.locator('#modal-home')
        assert home.locator('.team-name-zh').count() > 0
        assert home.locator('.team-name-en').count() > 0

    def test_away_team_has_flag(self, opened_modal):
        away = opened_modal.locator('#modal-away')
        flag = away.locator('.fi')
        assert flag.count() > 0

    def test_venue_shown(self, opened_modal):
        venue = opened_modal.locator('#modal-venue').text_content()
        # At least the location pin emoji
        assert "📍" in venue


class TestModalContentPlaceholder:
    """Verify modal shows correct placeholder info for R32 matches."""

    @pytest.fixture
    def opened_modal(self, page: Page):
        first_r32 = page.locator('.bracket-card.r32').first
        first_r32.click()
        page.wait_for_timeout(500)
        return page

    def test_placeholder_no_flag(self, opened_modal):
        """Placeholder teams have no flag (real country code absent)."""
        home = opened_modal.locator('#modal-home')
        # No .fi class, but has .placeholder-flag
        assert home.locator('.fi').count() == 0
        assert home.locator('.placeholder-flag').count() == 1

    def test_placeholder_described(self, opened_modal):
        """Placeholder text is shown with description."""
        home = opened_modal.locator('#modal-home')
        text = home.text_content().strip()
        # Should contain both the placeholder code and a description
        assert len(text) > 5  # not just "?"


class TestModalClose:
    def test_close_button(self, page: Page):
        page.locator('.bracket-card.r32').first.click()
        page.wait_for_timeout(500)
        page.click('.match-modal-close')
        page.wait_for_timeout(300)
        assert page.locator('#match-modal').get_attribute('hidden') is not None

    def test_backdrop_click(self, page: Page):
        page.locator('.bracket-card.r32').first.click()
        page.wait_for_timeout(500)
        # Click at top-left of viewport (definitely outside the centered card)
        page.mouse.click(20, 20)
        page.wait_for_timeout(300)
        assert page.locator('#match-modal').get_attribute('hidden') is not None

    def test_escape_key(self, page: Page):
        page.locator('.bracket-card.r32').first.click()
        page.wait_for_timeout(500)
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)
        assert page.locator('#match-modal').get_attribute('hidden') is not None


class TestModalVisual:
    def test_modal_screenshot(self, page: Page):
        """Save a screenshot of the modal for visual review."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        page.locator('#matches-view .match-card').first.click()
        page.wait_for_timeout(500)
        path = page.screenshot(path='tests/e2e/screenshots/modal_real.png', full_page=True)
        assert path
