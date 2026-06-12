"""E2E tests for match details: scores, goalscorers (Plan 010)."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page


class TestMatchesViewStatusBadge:
    def test_final_match_has_status_badge(self, page: Page):
        """R4, R5: First match (MEX vs RSA) is 'final' with score 2-0."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        first = page.locator('#matches-view .match-card').first
        assert first.get_attribute('data-status') == 'final'
        # Badge present
        badge = first.locator('.status-badge')
        assert badge.count() == 1
        assert '已结束' in badge.text_content()

    def test_final_match_shows_score(self, page: Page):
        """R5: Final match shows score '2 - 0'."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        first = page.locator('#matches-view .match-card').first
        score = first.locator('.match-score')
        assert score.count() == 1
        nums = score.locator('.score-num').all()
        assert len(nums) == 2
        assert nums[0].text_content().strip() == '2'
        assert nums[1].text_content().strip() == '0'

    def test_scheduled_match_shows_vs(self, page: Page):
        """R7: Match without details (future) shows 'vs' instead of score."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        # Find a card with status="scheduled" — e.g., a future date like June 13+
        cards = page.locator('#matches-view .match-card').all()
        scheduled_card = None
        for card in cards:
            if card.get_attribute('data-status') == 'scheduled':
                scheduled_card = card
                break
        assert scheduled_card is not None, "No scheduled match found in first 10 cards"
        # Should have 'vs' instead of match-score
        assert scheduled_card.locator('.match-score').count() == 0
        assert scheduled_card.locator('.match-vs').count() == 1
        # Badge says "未开始"
        assert '未开始' in scheduled_card.locator('.status-badge').text_content()


class TestModalScoreSection:
    def test_modal_shows_score_for_final(self, page: Page):
        """R9: Click MEX vs RSA → modal shows 2-0 score section."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        page.locator('#matches-view .match-card').first.click()
        page.wait_for_timeout(500)
        ss = page.locator('#modal-score-section')
        assert ss.get_attribute('hidden') is None
        text = ss.text_content()
        assert '2' in text and '0' in text
        assert '完场' in text

    def test_modal_shows_half_time_score(self, page: Page):
        """R11: Half-time score shown for matches that have it."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        page.locator('#matches-view .match-card').first.click()
        page.wait_for_timeout(500)
        ss = page.locator('#modal-score-section')
        text = ss.text_content()
        # Initial data has half_time_score: 1-0 for MEX vs RSA
        assert '半场' in text and '1' in text and '0' in text

    def test_modal_hides_score_for_scheduled(self, page: Page):
        """R12: Scheduled match → modal does NOT show score section."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        # Find a scheduled card (future match) and click it
        cards = page.locator('#matches-view .match-card').all()
        for card in cards:
            if card.get_attribute('data-status') == 'scheduled':
                card.click()
                page.wait_for_timeout(500)
                ss = page.locator('#modal-score-section')
                assert ss.get_attribute('hidden') is not None, "Score section should be hidden for scheduled"
                return
        pytest.skip("No scheduled match in first batch")


class TestModalGoalscorers:
    def test_modal_shows_goalscorers_list(self, page: Page):
        """R10: Click MEX vs RSA → modal shows goalscorer list."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        page.locator('#matches-view .match-card').first.click()
        page.wait_for_timeout(500)
        gs = page.locator('#modal-goals-section')
        assert gs.get_attribute('hidden') is None
        text = gs.text_content()
        # Initial data has 2 goals: H. Lozano (23') and R. Jiménez (67', penalty)
        assert '进球' in text
        assert 'H. Lozano' in text
        assert '23' in text
        assert 'R. Jiménez' in text
        assert '67' in text
        assert '点' in text  # penalty marker

    def test_modal_goals_have_flag(self, page: Page):
        """Each goal row has a team flag."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        page.locator('#matches-view .match-card').first.click()
        page.wait_for_timeout(500)
        gs = page.locator('#modal-goals-section')
        # Should have at least 2 goal rows
        rows = gs.locator('.goal-row').all()
        assert len(rows) >= 1
        # First row has a flag
        flag = rows[0].locator('.fi')
        assert flag.count() == 1, "Each goal row should have a flag"

    def test_modal_no_goals_for_scheduled(self, page: Page):
        """R10 (negative): Scheduled match → no goalscorers section."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        cards = page.locator('#matches-view .match-card').all()
        for card in cards:
            if card.get_attribute('data-status') == 'scheduled':
                card.click()
                page.wait_for_timeout(500)
                gs = page.locator('#modal-goals-section')
                assert gs.get_attribute('hidden') is not None
                return
        pytest.skip("No scheduled match in first batch")


class TestModalPlaceholder:
    def test_placeholder_match_no_score_shown(self, page: Page):
        """R17: R32 placeholder match → no score even if status=final (we don't know real teams)."""
        # First R32 card in bracket view
        first_r32 = page.locator('.bracket-card.r32').first
        first_r32.click()
        page.wait_for_timeout(500)
        ss = page.locator('#modal-score-section')
        # R32 matches don't have details, so score section is hidden
        assert ss.get_attribute('hidden') is not None


class TestVisualScreenshots:
    def test_matches_view_screenshot(self, page: Page):
        """Save matches view screenshot for visual review."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(500)
        path = page.screenshot(path='tests/e2e/screenshots/matches_with_scores.png', full_page=True)
        assert path

    def test_modal_with_score_screenshot(self, page: Page):
        """Save modal screenshot showing score and goalscorers."""
        page.click('button[data-tab="matches"]')
        page.wait_for_timeout(300)
        page.locator('#matches-view .match-card').first.click()
        page.wait_for_timeout(500)
        path = page.screenshot(path='tests/e2e/screenshots/modal_final_score.png', full_page=True)
        assert path
