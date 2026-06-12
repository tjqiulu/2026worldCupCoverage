"""Tests for country metadata + match enrichment."""
from pathlib import Path

import pytest

from src.data.countries import (
    all_countries,
    enrich_match,
    enrich_matches,
    is_placeholder,
    lookup,
)


# === Lookup ===

class TestLookup:
    def test_real_country(self):
        info = lookup("Mexico")
        assert info is not None
        assert info["name_zh"] == "墨西哥"
        assert info["code_iso"] == "mx"
        assert info["code_fifa"] == "MEX"

    def test_england_uses_subnational_flag(self):
        info = lookup("England")
        assert info is not None
        assert info["code_iso"] == "gb-eng"

    def test_scotland_uses_subnational_flag(self):
        info = lookup("Scotland")
        assert info is not None
        assert info["code_iso"] == "gb-sct"

    def test_unknown_returns_none(self):
        assert lookup("Atlantis") is None
        assert lookup("") is None
        assert lookup(None) is None

    def test_all_48_teams_have_entries(self):
        # The 48 qualified teams in baires ICS
        expected_teams = {
            "Algeria", "Argentina", "Australia", "Austria", "Belgium",
            "Bosnia & Herzegovina", "Brazil", "Canada", "Cape Verde", "Colombia",
            "Croatia", "Curaçao", "Czech Republic", "DR Congo", "Ecuador",
            "Egypt", "England", "France", "Germany", "Ghana", "Haiti", "Iran",
            "Iraq", "Ivory Coast", "Japan", "Jordan", "Mexico", "Morocco",
            "Netherlands", "New Zealand", "Norway", "Panama", "Paraguay",
            "Portugal", "Qatar", "Saudi Arabia", "Scotland", "Senegal",
            "South Africa", "South Korea", "Spain", "Sweden", "Switzerland",
            "Tunisia", "Turkey", "USA", "Uruguay", "Uzbekistan",
        }
        all_c = all_countries()
        assert set(all_c.keys()) == expected_teams, (
            f"Missing: {expected_teams - set(all_c.keys())}\n"
            f"Extra: {set(all_c.keys()) - expected_teams}"
        )

    def test_all_entries_have_required_fields(self):
        for name, info in all_countries().items():
            assert "name_zh" in info, f"{name} missing name_zh"
            assert "code_iso" in info, f"{name} missing code_iso"
            assert "code_fifa" in info, f"{name} missing code_fifa"
            assert len(info["code_iso"]) >= 2, f"{name} code_iso too short"
            assert info["name_zh"], f"{name} has empty name_zh"


# === is_placeholder ===

class TestIsPlaceholder:
    @pytest.mark.parametrize("name", [
        "1E", "2A", "3A/B/C/D/F", "W73", "W86", "L101", "L102", "1I", "3E/H/I/J/K",
    ])
    def test_placeholder_true(self, name):
        assert is_placeholder(name), f"Expected {name!r} to be a placeholder"

    @pytest.mark.parametrize("name", [
        "Mexico", "USA", "Brazil", "South Korea", "Ivory Coast", "Bosnia & Herzegovina",
    ])
    def test_real_country_false(self, name):
        assert not is_placeholder(name), f"Expected {name!r} to NOT be a placeholder"

    def test_empty_and_none(self):
        assert not is_placeholder("")
        assert not is_placeholder(None)


# === enrich_match ===

class TestEnrichMatch:
    def test_real_team_gets_zh_and_codes(self):
        m = {
            "match_id": "test-1",
            "home": {"name": "Mexico"},
            "away": {"name": "USA"},
        }
        enrich_match(m)
        assert m["home"]["name_zh"] == "墨西哥"
        assert m["home"]["code_iso"] == "mx"
        assert m["home"]["code_fifa"] == "MEX"
        assert m["away"]["name_zh"] == "美国"
        assert m["away"]["code_iso"] == "us"

    def test_placeholder_left_alone(self):
        m = {
            "match_id": "test-2",
            "home": {"name": "1E"},
            "away": {"name": "W86"},
        }
        enrich_match(m)
        assert "name_zh" not in m["home"]
        assert "code_iso" not in m["home"]
        assert "name_zh" not in m["away"]
        assert "code_iso" not in m["away"]

    def test_mixed_real_and_placeholder(self):
        m = {
            "match_id": "test-3",
            "home": {"name": "Brazil"},
            "away": {"name": "W86"},
        }
        enrich_match(m)
        assert m["home"]["name_zh"] == "巴西"
        assert m["home"]["code_iso"] == "br"
        assert "name_zh" not in m["away"]

    def test_unknown_team_doesnt_throw(self):
        m = {
            "match_id": "test-4",
            "home": {"name": "Atlantis"},
            "away": {"name": "Mexico"},
        }
        enrich_match(m)  # should not raise
        assert "name_zh" not in m["home"]
        assert m["away"]["name_zh"] == "墨西哥"

    def test_missing_side_safe(self):
        m = {"match_id": "test-5", "home": {"name": "Mexico"}}
        enrich_match(m)  # no 'away' key
        assert m["home"]["name_zh"] == "墨西哥"

    def test_empty_name_safe(self):
        m = {"match_id": "test-6", "home": {"name": ""}, "away": {"name": None}}
        enrich_match(m)  # should not raise
        assert "name_zh" not in m["home"]
        assert "name_zh" not in m["away"]

    def test_enrich_matches_bulk(self):
        matches = [
            {"match_id": "1", "home": {"name": "Mexico"}, "away": {"name": "USA"}},
            {"match_id": "2", "home": {"name": "Brazil"}, "away": {"name": "W86"}},
        ]
        enrich_matches(matches)
        assert matches[0]["home"]["name_zh"] == "墨西哥"
        assert matches[1]["home"]["name_zh"] == "巴西"
        assert "name_zh" not in matches[1]["away"]
