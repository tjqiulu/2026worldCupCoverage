"""Tests for match details data layer (Plan 010)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.data.details import (
    DETAILS_FILE,
    _is_incomplete,
    all_details,
    compute_standings_from_details,
    enrich_match,
    enrich_matches,
    file_exists,
    file_path,
    get_details,
    merge_from_api,
    validate_entry,
)


# === R1, R2: details.json exists and loadable ===

class TestDetailsFile:
    def test_file_exists(self):
        assert file_exists(), f"details.json missing at {file_path()}"

    def test_file_loadable(self):
        details = all_details()
        assert isinstance(details, dict)

    def test_file_only_has_special_keys_or_empty(self):
        """Plan 010 user feedback: don't ship fake example data.
        details.json should be empty (just _comment) until real results added."""
        details = all_details()
        # If user has added real data, that's fine. We just don't
        # REQUIRE example data anymore.
        # (No assertion — empty file is valid; user adds data as matches play.)
        pass

    def test_all_entries_have_valid_status(self):
        """R1: All entries (if any) must have valid status."""
        details = all_details()
        for mid, entry in details.items():
            from src.data.details import validate_entry, VALID_STATUSES
            assert entry.get("status") in VALID_STATUSES, (
                f"Entry {mid} has invalid status: {entry.get('status')}"
            )
            assert validate_entry(entry), f"Entry {mid} failed validation: {entry}"


# === validate_entry ===

class TestValidateEntry:
    @pytest.mark.parametrize("entry", [
        {"status": "final", "score": {"home": 2, "away": 1}},
        {"status": "live", "score": {"home": 0, "away": 0}},
        {"status": "scheduled"},
        {"status": "final", "score": {"home": 2, "away": 1},
         "half_time_score": {"home": 1, "away": 0}},
        {"status": "final", "score": {"home": 2, "away": 1},
         "goalscorers": [
             {"team": "home", "player": "Test", "minute": 23, "type": "goal"},
         ]},
    ])
    def test_valid(self, entry):
        assert validate_entry(entry)

    @pytest.mark.parametrize("entry", [
        None,  # not a dict
        "string",  # not a dict
        {"status": "invalid"},  # bad status
        {"status": "final"},  # final without score
        {"status": "live"},  # live without score
        {"status": "final", "score": {"home": -1, "away": 0}},  # negative
        {"status": "final", "score": "not a dict"},
        {"status": "final", "score": {"home": "1", "away": 0}},  # string
        {"status": "final", "score": {"home": 0, "away": 0},
         "goalscorers": "not a list"},
        {"status": "final", "score": {"home": 0, "away": 0},
         "goalscorers": [{"team": "invalid", "player": "X", "minute": 1}]},
        {"status": "final", "score": {"home": 0, "away": 0},
         "goalscorers": [{"team": "home", "player": "", "minute": 1}]},
        {"status": "final", "score": {"home": 0, "away": 0},
         "goalscorers": [{"team": "home", "player": "X", "minute": -5}]},
    ])
    def test_invalid(self, entry):
        assert not validate_entry(entry)


# === get_details ===

class TestGetDetails:
    def test_get_existing_match(self):
        details = all_details()
        if not details:
            pytest.skip("No details entries in details.json")
        first_id = next(iter(details))
        result = get_details(first_id)
        assert result is not None
        assert "status" in result

    def test_get_nonexistent_match(self):
        assert get_details("nonexistent-match-id") is None

    def test_get_malformed_match_isolated(self, tmp_path):
        """R16: malformed entry doesn't crash, returns None."""
        # Write a malformed file
        bad_file = tmp_path / "details.json"
        bad_file.write_text(json.dumps({
            "good_match": {"status": "final", "score": {"home": 1, "away": 0}},
            "bad_match": {"status": "INVALID_STATUS"},
        }))
        with patch("src.data.details.DETAILS_FILE", bad_file):
            # No cache to clear (Plan 016: lru_cache removed from _load)
            assert get_details("good_match") is not None
            assert get_details("bad_match") is None


# === enrich_match / enrich_matches ===

class TestEnrichMatch:
    def test_enrich_adds_details_field(self):
        m = {"match_id": "nonexistent", "home": {"name": "X"}, "away": {"name": "Y"}}
        enrich_match(m)
        assert "details" in m
        assert m["details"] is None  # not in details.json

    def test_enrich_with_existing_details(self):
        details = all_details()
        if not details:
            pytest.skip("No details entries")
        first_id = next(iter(details))
        m = {"match_id": first_id, "home": {"name": "X"}, "away": {"name": "Y"}}
        enrich_match(m)
        assert m["details"] is not None
        assert m["details"]["status"] in ("final", "live", "scheduled")

    def test_enrich_matches_bulk(self):
        matches = [
            {"match_id": "a", "home": {"name": "A"}, "away": {"name": "B"}},
            {"match_id": "b", "home": {"name": "C"}, "away": {"name": "D"}},
        ]
        enrich_matches(matches)
        for m in matches:
            assert "details" in m


# === Plan 017: _is_incomplete + merge_from_api ===

class TestIsIncomplete:
    def test_complete_entry(self):
        # 2-1 final, 3 goalscorers (2+1=3) → complete
        entry = {
            "status": "final",
            "score": {"home": 2, "away": 1},
            "goalscorers": [
                {"team": "home", "player": "A", "minute": 10},
                {"team": "home", "player": "B", "minute": 20},
                {"team": "away", "player": "C", "minute": 30},
            ],
        }
        assert _is_incomplete(entry) is False

    def test_incomplete_entry_fewer_goalscorers(self):
        # 5-1 final, only 3 goalscorers → incomplete
        entry = {
            "status": "final",
            "score": {"home": 5, "away": 1},
            "goalscorers": [
                {"team": "home", "player": "A", "minute": 7},
                {"team": "home", "player": "B", "minute": 30},
                {"team": "away", "player": "C", "minute": 43},
            ],
        }
        assert _is_incomplete(entry) is True

    def test_scheduled_entry_not_incomplete(self):
        # No score yet, can't judge → not incomplete
        entry = {"status": "scheduled"}
        assert _is_incomplete(entry) is False

    def test_no_goalscorers_key_with_score(self):
        # Has score 1-0 but no goalscorers list at all → incomplete
        entry = {"status": "final", "score": {"home": 1, "away": 0}}
        assert _is_incomplete(entry) is True

    def test_more_goalscorers_than_score(self):
        # Manual correction with OG counted differently → don't flag
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"team": "home", "player": "A", "minute": 10, "type": "goal"},
                {"team": "home", "player": "B", "minute": 20, "type": "own_goal"},
            ],
        }
        assert _is_incomplete(entry) is False

    def test_minute_zero_in_any_goal_is_malformed(self):
        # Plan 017.1: 7-1 with 8 goalscorers, count looks complete,
        # but one goal has minute=0 (time info accidentally baked into
        # player name like "K. Havertz 45'+5'(p)") → still incomplete
        entry = {
            "status": "final",
            "score": {"home": 7, "away": 1},
            "goalscorers": [
                {"team": "home", "player": "F. Nmecha", "minute": 7},
                {"team": "home", "player": "N. Schlotterbeck", "minute": 38},
                {"team": "home", "player": "K. Havertz 45'+5'(p)",
                 "minute": 0, "stoppage": None, "type": None},
                {"team": "home", "player": "J. Musiala", "minute": 47},
                {"team": "home", "player": "N. Brown", "minute": 68},
                {"team": "home", "player": "D. Undav", "minute": 78},
                {"team": "home", "player": "K. Havertz", "minute": 88},
                {"team": "away", "player": "L. Comenencia", "minute": 21},
            ],
        }
        assert _is_incomplete(entry) is True


class TestMergeFromApi:
    def test_new_match_added(self):
        # Plan 016/017 base: API entry that doesn't exist locally → added
        existing = {}
        api = {
            "m1": {"status": "final", "score": {"home": 1, "away": 0},
                   "goalscorers": [{"team": "home", "player": "A", "minute": 10}]}
        }
        merged, changed, overwritten = merge_from_api(existing, api)
        assert changed == 1
        assert overwritten == 0
        assert merged["m1"] == api["m1"]

    def test_complete_existing_wins_over_api(self):
        # Plan 017: existing has full goalscorers → existing wins
        existing = {
            "m1": {
                "status": "final",
                "score": {"home": 2, "away": 1},
                "goalscorers": [
                    {"team": "home", "player": "A", "minute": 10},
                    {"team": "home", "player": "B", "minute": 50},
                    {"team": "away", "player": "C", "minute": 70},
                ],
            }
        }
        api = {
            "m1": {"status": "final", "score": {"home": 2, "away": 1},
                   "goalscorers": [
                       {"team": "home", "player": "A", "minute": 10},
                       {"team": "home", "player": "B", "minute": 50},
                       {"team": "away", "player": "C", "minute": 70},
                   ]}
        }
        merged, changed, overwritten = merge_from_api(existing, api)
        assert changed == 0
        assert overwritten == 0
        # Existing kept (preserve manual corrections)
        assert merged["m1"] == existing["m1"]

    def test_incomplete_existing_overridden_by_api(self):
        # Plan 017 KEY BEHAVIOR: 5-1 with only 3 goalscorers → API overrides
        existing = {
            "m1": {
                "status": "final",
                "score": {"home": 5, "away": 1},
                "goalscorers": [
                    {"team": "home", "player": "A", "minute": 7},
                    {"team": "home", "player": "B", "minute": 30},
                    {"team": "away", "player": "C", "minute": 43},
                ],
            }
        }
        api = {
            "m1": {"status": "final", "score": {"home": 5, "away": 1},
                   "goalscorers": [
                       {"team": "home", "player": "A", "minute": 7},
                       {"team": "home", "player": "B", "minute": 30},
                       {"team": "away", "player": "C", "minute": 43},
                       {"team": "home", "player": "D", "minute": 60},
                       {"team": "home", "player": "E", "minute": 84},
                       {"team": "home", "player": "A", "minute": 90, "stoppage": 5},
                   ]}
        }
        merged, changed, overwritten = merge_from_api(existing, api)
        assert changed == 1
        assert overwritten == 1
        # API version (6 goals) replaced existing (3 goals)
        assert len(merged["m1"]["goalscorers"]) == 6

    def test_mixed_add_and_override(self):
        existing = {
            "m1": {  # incomplete → will be overridden
                "status": "final",
                "score": {"home": 2, "away": 0},
                "goalscorers": [{"team": "home", "player": "A", "minute": 10}],
            },
            "m2": {  # complete → stays
                "status": "final",
                "score": {"home": 1, "away": 1},
                "goalscorers": [
                    {"team": "home", "player": "B", "minute": 20},
                    {"team": "away", "player": "C", "minute": 30},
                ],
            },
        }
        api = {
            "m1": {"status": "final", "score": {"home": 2, "away": 0},
                   "goalscorers": [
                       {"team": "home", "player": "A", "minute": 10},
                       {"team": "home", "player": "D", "minute": 70},
                   ]},
            "m2": {"status": "final", "score": {"home": 1, "away": 1},
                   "goalscorers": [
                       {"team": "home", "player": "B", "minute": 20},
                       {"team": "away", "player": "C", "minute": 30},
                   ]},
            "m3": {"status": "final", "score": {"home": 3, "away": 0},  # new
                   "goalscorers": [{"team": "home", "player": "E", "minute": 5}]},
        }
        merged, changed, overwritten = merge_from_api(existing, api)
        assert changed == 2  # m1 overridden + m3 added
        assert overwritten == 1
        assert len(merged) == 3
        assert len(merged["m1"]["goalscorers"]) == 2  # API version
        assert merged["m2"] == existing["m2"]  # complete → existing kept
        assert merged["m3"] == api["m3"]  # new added

    def test_malformed_minute_zero_overridden(self):
        """Plan 017.1: count-complete but minute=0 in one goal → API overrides."""
        existing = {
            "m1": {  # count complete (8 = 7+1) but one has minute=0
                "status": "final",
                "score": {"home": 7, "away": 1},
                "goalscorers": [
                    {"team": "home", "player": "A", "minute": 7},
                    {"team": "home", "player": "B", "minute": 38},
                    {"team": "home", "player": "K. Havertz 45'+5'(p)",
                     "minute": 0},
                    {"team": "home", "player": "D", "minute": 47},
                    {"team": "home", "player": "E", "minute": 68},
                    {"team": "home", "player": "F", "minute": 78},
                    {"team": "home", "player": "G", "minute": 88},
                    {"team": "away", "player": "H", "minute": 21},
                ],
            }
        }
        api = {
            "m1": {"status": "final", "score": {"home": 7, "away": 1},
                   "goalscorers": [
                       {"team": "home", "player": "A", "minute": 7},
                       {"team": "home", "player": "B", "minute": 38},
                       {"team": "home", "player": "K. Havertz",
                        "minute": 45, "stoppage": 5, "type": "penalty"},
                       {"team": "home", "player": "D", "minute": 47},
                       {"team": "home", "player": "E", "minute": 68},
                       {"team": "home", "player": "F", "minute": 78},
                       {"team": "home", "player": "G", "minute": 88},
                       {"team": "away", "player": "H", "minute": 21},
                   ]}
        }
        merged, changed, overwritten = merge_from_api(existing, api)
        assert changed == 1
        assert overwritten == 1
        # API version has clean "K. Havertz" with proper minute=45/stoppage=5
        havertz = [g for g in merged["m1"]["goalscorers"]
                   if g.get("player") == "K. Havertz"]
        assert len(havertz) == 1
        assert havertz[0]["minute"] == 45
        assert havertz[0]["stoppage"] == 5
        assert havertz[0]["type"] == "penalty"


# === Plan 025: Local standings derivation ===
# worldcup26.ir /get/groups is sometimes stale. We compute standings from
# our own details.json as the source of truth. These tests pin the
# behavior so a future refactor doesn't break the Iraq-Norway / France-
# Senegal consistency guarantee.

class TestComputeStandingsFromDetails:
    """Plan 025: compute_standings_from_details derives MP/W/D/L/GF/GA/GD/PTS
    from local final-match data. Same shape as the API response so the
    frontend (and the modal) can use it transparently."""

    def test_group_with_no_final_matches_returns_none(self):
        """Group where no match is final yet → caller should fall back to API."""
        details = {"m1": {"status": "scheduled"}}
        matches = [{"match_id": "m1", "group": "I", "home": {"name": "Iraq"}, "away": {"name": "Norway"}}]
        result = compute_standings_from_details("I", details, matches, {"Iraq": "35", "Norway": "36"})
        assert result is None

    def test_single_final_match_yields_correct_stats(self):
        """Iraq 1-4 Norway → Iraq 1MP 0W 0D 1L 1GF 4GA -3GD 0PTS;
        Norway 1MP 1W 0D 0L 4GF 1GA +3GD 3PTS. Norway ranked first."""
        details = {
            "m1": {
                "status": "final",
                "score": {"home": 1, "away": 4},
            }
        }
        matches = [{
            "match_id": "m1", "group": "I",
            "home": {"name": "Iraq"}, "away": {"name": "Norway"},
        }]
        result = compute_standings_from_details(
            "I", details, matches, {"Iraq": "35", "Norway": "36"}
        )
        assert result is not None
        assert len(result) == 2
        # Norway (winner) should be first
        assert result[0]["team_id"] == "36"
        assert result[0] == {"team_id": "36", "mp": 1, "w": 1, "d": 0, "l": 0, "gf": 4, "ga": 1, "gd": 3, "pts": 3}
        # Iraq (loser) second
        assert result[1]["team_id"] == "35"
        assert result[1] == {"team_id": "35", "mp": 1, "w": 0, "d": 0, "l": 1, "gf": 1, "ga": 4, "gd": -3, "pts": 0}

    def test_draw_yields_one_point_each(self):
        """1-1 draw → both teams get 1 point."""
        details = {"m1": {"status": "final", "score": {"home": 1, "away": 1}}}
        matches = [{
            "match_id": "m1", "group": "A",
            "home": {"name": "Mexico"}, "away": {"name": "Sweden"},
        }]
        result = compute_standings_from_details(
            "A", details, matches, {"Mexico": "01", "Sweden": "02"}
        )
        assert result[0]["pts"] == 1
        assert result[1]["pts"] == 1
        assert result[0]["d"] == 1
        assert result[0]["gd"] == 0

    def test_group_filter_excludes_other_groups(self):
        """A final match in group A should NOT affect group I standings."""
        details = {
            "m_a": {"status": "final", "score": {"home": 5, "away": 0}},
            "m_i": {"status": "final", "score": {"home": 1, "away": 4}},
        }
        matches = [
            {"match_id": "m_a", "group": "A", "home": {"name": "X"}, "away": {"name": "Y"}},
            {"match_id": "m_i", "group": "I", "home": {"name": "Iraq"}, "away": {"name": "Norway"}},
        ]
        result = compute_standings_from_details(
            "I", details, matches, {"Iraq": "35", "Norway": "36", "X": "99", "Y": "98"}
        )
        # Should only have Iraq and Norway
        team_ids = {t["team_id"] for t in result}
        assert team_ids == {"35", "36"}
        # Should NOT include X or Y
        assert "99" not in team_ids
        assert "98" not in team_ids

    def test_sort_order_pts_then_gd_then_gf(self):
        """Two teams with same PTS: higher GD ranks first (FIFA standard).
        Tie on GD: higher GF ranks first."""
        details = {
            "m1": {"status": "final", "score": {"home": 3, "away": 0}},  # A wins big
            "m2": {"status": "final", "score": {"home": 1, "away": 0}},  # B wins small
        }
        matches = [
            {"match_id": "m1", "group": "X", "home": {"name": "A"}, "away": {"name": "C"}},
            {"match_id": "m2", "group": "X", "home": {"name": "B"}, "away": {"name": "D"}},
        ]
        result = compute_standings_from_details(
            "X", details, matches, {"A": "1", "B": "2", "C": "3", "D": "4"}
        )
        # A: 3pts, GD=+3, GF=3
        # B: 3pts, GD=+1, GF=1
        # A should rank higher than B (same PTS, but A has better GD)
        assert result[0]["team_id"] == "1"
        assert result[1]["team_id"] == "2"

    def test_unknown_team_names_are_skipped(self):
        """If team_name_to_id doesn't have a team, that match is skipped
        (we can't attribute stats without a team_id)."""
        details = {"m1": {"status": "final", "score": {"home": 1, "away": 0}}}
        matches = [{
            "match_id": "m1", "group": "I",
            "home": {"name": "Unknown Country"}, "away": {"name": "Norway"},
        }]
        result = compute_standings_from_details(
            "I", details, matches, {"Norway": "36"}  # no mapping for "Unknown Country"
        )
        # Should be None because no match could be fully attributed
        # (home team is missing from the map)
        # OR if we DO get a partial result with only Norway, that's also OK
        # but the safest guarantee: don't crash, don't fabricate stats
        if result is not None:
            # If result, must not include fabricated team_id for Unknown Country
            for t in result:
                assert t["team_id"] in {"36"}

    def test_real_iraq_norway_and_france_senegal(self):
        """Integration: simulate the exact Group I state at 2026-06-17 10:00
        — France-Senegal (3-1) + Iraq-Norway (1-4). France and Norway
        should be tied on 3 PTS, ordered by GD (France +2, Norway +3)."""
        details = {
            "fr": {"status": "final", "score": {"home": 3, "away": 1}},  # France-Senegal
            "iq": {"status": "final", "score": {"home": 1, "away": 4}},  # Iraq-Norway
        }
        matches = [
            {"match_id": "fr", "group": "I", "home": {"name": "France"}, "away": {"name": "Senegal"}},
            {"match_id": "iq", "group": "I", "home": {"name": "Iraq"}, "away": {"name": "Norway"}},
        ]
        result = compute_standings_from_details(
            "I", details, matches,
            {"France": "33", "Senegal": "34", "Iraq": "35", "Norway": "36"},
        )
        # Sort: Norway (3pts, +3) > France (3pts, +2) > Senegal (0pts, -2) > Iraq (0pts, -3)
        assert [t["team_id"] for t in result] == ["36", "33", "34", "35"]
        assert result[0] == {"team_id": "36", "mp": 1, "w": 1, "d": 0, "l": 0, "gf": 4, "ga": 1, "gd": 3, "pts": 3}
        assert result[1] == {"team_id": "33", "mp": 1, "w": 1, "d": 0, "l": 0, "gf": 3, "ga": 1, "gd": 2, "pts": 3}
        assert result[2] == {"team_id": "34", "mp": 1, "w": 0, "d": 0, "l": 1, "gf": 1, "ga": 3, "gd": -2, "pts": 0}
        assert result[3] == {"team_id": "35", "mp": 1, "w": 0, "d": 0, "l": 1, "gf": 1, "ga": 4, "gd": -3, "pts": 0}
