"""E2E tests for Plan 015 (detail page content enrichment).

Tests:
- API: /api/teams returns 48 teams with code_iso
- API: /api/matches enriches each match with venue.stadium (where matchable)
- API: /api/matches adds standings to group-stage matches
- UI: Modal shows stadium section for all matches
- UI: Modal shows standings table for group stage
- UI: Modal shows countdown for upcoming matches
- UI: Countdown updates over time
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page


# === API tests (no browser needed) ===

class TestApiTeams:
    def test_teams_endpoint_returns_48(self, page: Page):
        resp = page.request.get("http://127.0.0.1:8766/api/teams")
        assert resp.ok
        teams = resp.json()
        assert len(teams) == 48, f"Expected 48 teams, got {len(teams)}"
        # Each team should have required fields
        mexico = teams.get("1")
        assert mexico is not None
        assert mexico["name"] == "Mexico"
        assert mexico["name_zh"] == "墨西哥"
        assert mexico["code_iso"] == "mx"
        assert mexico["code_fifa"] == "MEX"


class TestApiMatchesEnrichment:
    def test_matches_have_stadium(self, page: Page):
        resp = page.request.get("http://127.0.0.1:8766/api/matches")
        matches = resp.json()
        # At least one match should have a stadium enriched
        with_stadium = [m for m in matches if m.get("venue", {}).get("stadium")]
        assert len(with_stadium) >= 50, f"Only {len(with_stadium)} matches have stadium"
        s = with_stadium[0]["venue"]["stadium"]
        assert s["name"]
        assert s["city"]
        assert s["country"]
        assert s["capacity"] > 0

    def test_group_matches_have_standings(self, page: Page):
        resp = page.request.get("http://127.0.0.1:8766/api/matches")
        matches = resp.json()
        # Find a finished group match
        group_matches = [m for m in matches
                         if m.get("stage") == "group" and m.get("group")]
        with_standings = [m for m in group_matches if m.get("standings")]
        assert len(with_standings) >= 1, "No group matches have standings"
        # Each standings entry should have 4 teams
        for m in with_standings[:3]:
            assert len(m["standings"]) == 4
            for t in m["standings"]:
                assert "team_id" in t
                assert "pts" in t

    def test_knockout_matches_no_standings(self, page: Page):
        resp = page.request.get("http://127.0.0.1:8766/api/matches")
        matches = resp.json()
        knockout = [m for m in matches if m.get("stage") in ("r32", "r16", "qf", "sf", "final", "third")]
        # Knockout matches should NOT have standings
        for m in knockout[:5]:
            assert "standings" not in m, f"{m['stage']} match has standings"


# === UI tests ===

def _open_first_group_modal(page: Page) -> None:
    """Open the first match in the matches view (which is a group match)."""
    page.click('button.tab[data-tab="matches"]')
    page.wait_for_selector('#matches-view.active .match-card', timeout=10_000)
    page.locator('#matches-view .match-card').first.click()
    page.wait_for_selector('#match-modal:not([hidden])', timeout=5_000)
    # Wait for teams map + render
    page.wait_for_timeout(1500)


def _open_knockout_modal(page: Page) -> None:
    """Open a knockout match (R32) to check no standings section."""
    page.click('button.tab[data-tab="matches"]')
    page.wait_for_selector('#matches-view.active .match-card', timeout=10_000)
    # Find a knockout card (stage data attr or by class). Use a known index range.
    cards = page.locator('#matches-view .match-card')
    # Group stage = first 72 matches; R32 starts at 72
    cards.nth(75).click()
    page.wait_for_selector('#match-modal:not([hidden])', timeout=5_000)
    page.wait_for_timeout(1000)


class TestStadiumSection:
    def test_stadium_section_visible_for_group_match(self, page: Page):
        _open_first_group_modal(page)
        section = page.locator('#modal-stadium-section')
        assert section.is_visible()
        # Should have stadium name + capacity
        name = page.locator('#modal-stadium-section .stadium-name')
        assert name.count() == 1
        assert name.text_content().strip() != ""
        cap = page.locator('#modal-stadium-section .stadium-capacity')
        assert cap.count() == 1
        assert "Capacity" in cap.text_content()

    def test_stadium_section_visible_for_knockout(self, page: Page):
        _open_knockout_modal(page)
        section = page.locator('#modal-stadium-section')
        # Knockout matches also have venue (just no standings)
        assert section.is_visible(), "Stadium should show for knockout too"


class TestStandingsSection:
    def test_standings_section_for_group_match(self, page: Page):
        _open_first_group_modal(page)
        section = page.locator('#modal-standings-section')
        assert section.is_visible(), "Group match should show standings"
        # Table should have 4 rows + header
        rows = page.locator('#modal-standings-section .standings-row')
        assert rows.count() == 4, f"Expected 4 standings rows, got {rows.count()}"
        # Header should have 7 columns
        headers = page.locator('#modal-standings-section thead th')
        assert headers.count() == 7

    def test_standings_section_hidden_for_knockout(self, page: Page):
        _open_knockout_modal(page)
        section = page.locator('#modal-standings-section')
        # Knockout matches don't have standings
        assert not section.is_visible(), "Standings should be hidden for knockout"

    def test_standings_rows_have_team_names(self, page: Page):
        _open_first_group_modal(page)
        names = page.locator('#modal-standings-section .standings-name')
        assert names.count() == 4
        for i in range(4):
            n = names.nth(i).text_content().strip()
            assert n and n != "Team ", f"Row {i} has no team name: '{n}'"

    def test_standings_rows_have_flag_icons(self, page: Page):
        _open_first_group_modal(page)
        flags = page.locator('#modal-standings-section .standings-flag .fi')
        assert flags.count() == 4, f"Expected 4 flag icons, got {flags.count()}"


class TestCountdownSection:
    def test_countdown_for_upcoming_match(self, page: Page):
        # Robustly find an upcoming match by status, not by index
        target = page.evaluate("""() => {
            const m = allMatches.find(m => m.date_utc > new Date().toISOString());
            return m ? m.match_id : null;
        }""")
        if not target:
            pytest.skip("No upcoming match in data (tournament may be over)")
        page.click('button.tab[data-tab="matches"]')
        page.wait_for_selector('#matches-view.active .match-card', timeout=10_000)
        page.click(f'[data-id="{target}"]')
        page.wait_for_selector('#match-modal:not([hidden])', timeout=5_000)
        page.wait_for_timeout(800)
        cd = page.locator('#modal-countdown-section')
        assert cd.is_visible(), "Countdown section should be visible for upcoming match"
        time_text = page.locator('#modal-countdown-time').text_content()
        assert time_text and time_text != "--:--:--"
        assert "天" in time_text or ":" in time_text
        page.screenshot(path="tests/e2e/screenshots/modal_countdown.png", full_page=True)

    def test_countdown_updates_over_time(self, page: Page):
        # Find any upcoming match
        target = page.evaluate("""() => {
            const m = allMatches.find(m => m.date_utc > new Date().toISOString());
            return m ? m.match_id : null;
        }""")
        if not target:
            pytest.skip("No upcoming match in data")
        page.click('button.tab[data-tab="matches"]')
        page.wait_for_selector('#matches-view.active .match-card', timeout=10_000)
        page.click(f'[data-id="{target}"]')
        page.wait_for_selector('#match-modal:not([hidden])', timeout=5_000)
        page.wait_for_timeout(500)
        assert page.locator('#modal-countdown-section').is_visible()
        t1 = page.locator('#modal-countdown-time').text_content()
        page.wait_for_timeout(1500)
        t2 = page.locator('#modal-countdown-time').text_content()
        assert t1 != t2, f"Countdown didn't update: {t1} == {t2}"

    def test_countdown_hidden_for_finished(self, page: Page):
        _open_first_group_modal(page)
        # MEX vs RSA is finished (2-0) — should NOT show countdown
        cd = page.locator('#modal-countdown-section')
        assert not cd.is_visible(), "Countdown should be hidden for finished matches"


class TestApiStadiumRobustness:
    """Test backend handles various venue names."""

    def test_all_ics_cities_have_stadium(self):
        """Every ICS city should map to a stadium (16 cities, 16 stadiums)."""
        from src.data.worldcup_api import find_stadium_by_city
        # The 16 WC 2026 host cities
        cities = [
            "Atlanta", "Boston (Foxborough)", "Dallas (Arlington)",
            "Guadalajara (Zapopan)", "Houston", "Kansas City",
            "Los Angeles (Inglewood)", "Mexico City", "Miami (Miami Gardens)",
            "Monterrey (Guadalupe)", "New York/New Jersey (East Rutherford)",
            "Philadelphia", "San Francisco Bay Area (Santa Clara)",
            "Seattle", "Toronto", "Vancouver",
        ]
        matched = 0
        unmatched = []
        for c in cities:
            s = find_stadium_by_city(c)
            if s is None:
                unmatched.append(c)
            else:
                matched += 1
        assert matched == 16, f"Unmatched cities: {unmatched}"
