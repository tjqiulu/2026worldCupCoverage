"""Tests for match details data layer (Plan 010)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.data.details import (
    DETAILS_FILE,
    _is_incomplete,
    _norm_team_key,
    all_details,
    apply_scorer_overrides,
    build_team_id_map,
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


# === Plan 026: Arabic -> English scorer name overrides ===

class TestScorerOverrides:
    """Unit tests for apply_scorer_overrides() and _load_overrides().

    Plan 026 fix: defends against the Belgium vs Egypt 阿语 display bug
    by maintaining a manual mapping table that runs after API parse.
    """

    def test_arabic_player_transliterated(self):
        """A goalscorer with Arabic player name gets replaced by English."""
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 1},
            "goalscorers": [
                {"player": "محمد هانی", "minute": 66, "type": None, "team": "home"},
            ],
        }
        out = apply_scorer_overrides(entry)
        assert out["goalscorers"][0]["player"] == "Mohamed Hany"
        assert out["goalscorers"][0]["minute"] == 66
        assert out["goalscorers"][0]["type"] is None
        assert out["goalscorers"][0]["team"] == "home"
        # Original entry not mutated
        assert entry["goalscorers"][0]["player"] == "محمد هانی"

    def test_english_player_unchanged(self):
        """A non-Arabic player is passed through untouched."""
        entry = {
            "status": "final",
            "score": {"home": 2, "away": 1},
            "goalscorers": [
                {"player": "K. Mbappé", "minute": 66, "type": "goal", "team": "home"},
                {"player": "B. Barcola", "minute": 82, "type": "goal", "team": "home"},
            ],
        }
        out = apply_scorer_overrides(entry)
        assert out is entry  # no change, returns same object
        assert out["goalscorers"][0]["player"] == "K. Mbappé"
        assert out["goalscorers"][1]["player"] == "B. Barcola"

    def test_unknown_arabic_passthrough(self):
        """Arabic player not in the override map is passed through untouched.

        We use a real Arabic name that is NOT in our map (e.g. a future
        Saudi Arabian goalscorer we haven't added yet) to make sure the
        code does not silently drop unknown Arabic.
        """
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"player": "سالم الدوسري", "minute": 30, "type": "goal", "team": "home"},
            ],
        }
        out = apply_scorer_overrides(entry)
        # Not in map -> unchanged
        assert out["goalscorers"][0]["player"] == "سالم الدوسري"

    def test_empty_overrides_file(self, tmp_path, monkeypatch):
        """If scorer_overrides.json is missing/empty, apply is a no-op."""
        monkeypatch.setattr("src.data.details._PROJECT_ROOT", tmp_path)
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"player": "محمد هانی", "minute": 66, "type": None, "team": "home"},
            ],
        }
        out = apply_scorer_overrides(entry)
        # File missing -> no mappings -> entry returned unchanged
        assert out is entry
        assert out["goalscorers"][0]["player"] == "محمد هانی"

    def test_apply_after_api_parse(self, monkeypatch):
        """Simulate API returning Arabic: post-_parse_scorer_strings the
        entry has Arabic in `player`; apply_scorer_overrides converts it
        to English so UI never sees Arabic."""
        # Mock the API parse path
        monkeypatch.setattr(
            "src.data.worldcup_api._fetch_endpoint",
            lambda *a, **kw: {
                "games": [
                    {
                        "home_team_name_en": "Belgium",
                        "away_team_name_en": "Egypt",
                        "home_scorers": '{"محمد هانی 66\'"}',
                        "away_scorers": '{"امام آشور 19\'"}',
                        "home_score": "1",
                        "away_score": "1",
                        "finished": "TRUE",
                    }
                ]
            },
        )
        from src.data.worldcup_api import game_to_details_entry
        api_entry = game_to_details_entry(
            {
                "home_team_name_en": "Belgium",
                "away_team_name_en": "Egypt",
                "home_scorers": '{"محمد هانی 66\'"}',
                "away_scorers": '{"امام آشور 19\'"}',
                "home_score": "1",
                "away_score": "1",
                "finished": "TRUE",
            }
        )
        # Pre-override: Arabic
        assert api_entry["goalscorers"][0]["player"] == "محمد هانی"
        assert api_entry["goalscorers"][1]["player"] == "امام آشور"
        # Apply overrides
        out = apply_scorer_overrides(api_entry)
        assert out["goalscorers"][0]["player"] == "Mohamed Hany"
        assert out["goalscorers"][1]["player"] == "Emam Ashour"

    def test_overrides_json_malformed(self, tmp_path, monkeypatch, caplog):
        """If scorer_overrides.json has invalid JSON, apply is a no-op
        and a warning is logged. The app must not crash on bad input.

        Audit fix (suggestion 3): defends against the file being
        hand-edited into a broken state.
        """
        import logging
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "scorer_overrides.json").write_text(
            "{ this is not valid json", encoding="utf-8"
        )
        monkeypatch.setattr("src.data.details._PROJECT_ROOT", tmp_path)
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"player": "محمد هانی", "minute": 66, "type": None, "team": "home"},
            ],
        }
        with caplog.at_level(logging.WARNING, logger="src.data.details"):
            out = apply_scorer_overrides(entry)
        # Malformed file -> no mappings -> entry returned unchanged
        assert out is entry
        assert out["goalscorers"][0]["player"] == "محمد هانی"
        # Warning was logged
        assert any("scorer_overrides.json load failed" in r.message for r in caplog.records)

    def test_arabic_with_latin_suffix(self):
        """A player name that mixes Arabic and Latin (e.g. 'محمد Salah')
        is NOT replaced, because the override is exact-match on the
        Arabic name. Audit fix (suggestion 3)."""
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                # This is NOT in the map as the Arabic exact form is "محمد صلاح"
                {"player": "محمد Salah", "minute": 30, "type": "goal", "team": "home"},
            ],
        }
        out = apply_scorer_overrides(entry)
        # Mixed Arabic+Latin not in map -> unchanged
        assert out["goalscorers"][0]["player"] == "محمد Salah"


# === Plan 027: Team-name alias resolver ===
# worldcup26.ir API and baires ICS use slightly different strings for the
# same team. Without normalization, compute_standings_from_details
# silently drops any match whose team names don't match exactly.

class TestNormTeamKey:
    """Unit tests for _norm_team_key (Plan 027 helper)."""

    def test_ampersand_to_and(self):
        assert _norm_team_key("Bosnia & Herzegovina") == "bosnia and herzegovina"

    def test_lowercases(self):
        assert _norm_team_key("USA") == "usa"
        assert _norm_team_key("United States") == "united states"

    def test_collapses_whitespace(self):
        assert _norm_team_key("  multiple   spaces  ") == "multiple spaces"

    def test_strips_punctuation(self):
        # Strips ASCII punctuation but preserves Unicode letters (so
        # "Côte d'Ivoire" still matches "Cote dIvoire" once lowercased,
        # and "Curaçao" stays "curaçao" — they collapse on whitespace
        # + lowercase only).
        assert _norm_team_key("Côte d'Ivoire") == "côte divoire"
        assert _norm_team_key("Curaçao") == "curaçao"
        # ASCII punctuation IS stripped:
        assert _norm_team_key("U.S.A.") == "usa"
        assert _norm_team_key("Korea Republic") == "korea republic"

    def test_empty_input(self):
        assert _norm_team_key("") == ""
        assert _norm_team_key(None) == ""  # type: ignore[arg-type]


class TestBuildTeamIdMap:
    """Unit tests for build_team_id_map (Plan 027).

    Covers the bug where baires ICS uses 'Bosnia & Herzegovina' /
    'USA' / 'DR Congo' but worldcup26.ir API uses 'Bosnia and
    Herzegovina' / 'United States' / 'Democratic Republic of the
    Congo'. The resolver must let compute_standings_from_details()
    resolve the ICS strings to the same team_id as the API strings.
    """

    def _sample_teams(self):
        """Minimal 5-team subset to exercise the resolver."""
        return {
            "5":  {"id": "5",  "name_en": "Canada",
                   "fifa_code": "CAN", "iso2": "CA"},
            "6":  {"id": "6",  "name_en": "Bosnia and Herzegovina",
                   "fifa_code": "BIH", "iso2": "BA"},
            "7":  {"id": "7",  "name_en": "Qatar",
                   "fifa_code": "QAT", "iso2": "QA"},
            "8":  {"id": "8",  "name_en": "Switzerland",
                   "fifa_code": "SUI", "iso2": "CH"},
            "13": {"id": "13", "name_en": "United States",
                   "fifa_code": "USA", "iso2": "US"},
        }

    def test_basic_name_en_match(self):
        m = build_team_id_map(self._sample_teams())
        assert m["Canada"] == "5"
        assert m["Qatar"] == "7"
        assert m["Switzerland"] == "8"

    def test_fifa_code_fallback(self):
        """ICS uses 'USA' (fifa_code) instead of 'United States' (name_en).
        Map must accept both keys."""
        m = build_team_id_map(self._sample_teams())
        assert m["USA"] == "13"
        assert m["United States"] == "13"

    def test_iso2_fallback(self):
        m = build_team_id_map(self._sample_teams())
        assert m["US"] == "13"

    def test_ampersand_normalized_match(self):
        """The bug case: ICS says 'Bosnia & Herzegovina' but API says
        'Bosnia and Herzegovina'. The normalized form of the ICS name
        (after & → and) must match the API's name_en."""
        m = build_team_id_map(self._sample_teams())
        # API's "Bosnia and Herzegovina" is in map literally (via name_en)
        assert m["Bosnia and Herzegovina"] == "6"
        # The normalized key for "Bosnia & Herzegovina" must also resolve
        # (compute_standings_from_details calls _norm_team_key on the
        # ICS home.name string before looking up the map).
        assert m[_norm_team_key("Bosnia & Herzegovina")] == "6"

    def test_priority_name_en_over_iso2(self):
        """name_en takes precedence over fifa_code and iso2. If two teams
        somehow collide on a key, first-inserted wins."""
        teams = {
            "1": {"id": "1", "name_en": "AAA",
                  "fifa_code": "X", "iso2": "X"},
            "2": {"id": "2", "name_en": "BBB",
                  "fifa_code": "Y", "iso2": "Y"},
        }
        m = build_team_id_map(teams)
        # name_en "AAA" inserted before any other key
        assert m["X"] == "1"  # from team 1's fifa_code/iso2
        assert m["AAA"] == "1"
        assert m["BBB"] == "2"

    def test_empty_team_dict_returns_empty_map(self):
        assert build_team_id_map({}) == {}

    def test_team_dict_missing_optional_fields(self):
        """If a team dict is missing name_en/fifa_code/iso2, we just
        skip those keys; the resolver must not crash."""
        teams = {
            "1": {"id": "1"},  # all optional fields missing
            "2": {"id": "2", "name_en": "Brazil"},
        }
        m = build_team_id_map(teams)
        # Empty team: only id "1" exists but has no keys → not in map
        assert "1" not in m
        assert m["Brazil"] == "2"

    def test_countries_reverse_lookup_abbreviation(self):
        """countries.json (keyed by ICS-style names) bridges abbreviations
        that _norm_team_key cannot derive from the API name. E.g. ICS
        'DR Congo' ↔ API 'Democratic Republic of the Congo' cannot be
        derived by character normalization — needs the countries.json
        code_fifa bridge."""
        # Sample countries.json-style entry
        countries = {
            "DR Congo": {"code_iso": "cd", "code_fifa": "COD"},
            "USA": {"code_iso": "us", "code_fifa": "USA"},
        }
        # Sample API teams
        teams = {
            "42": {"id": "42", "name_en": "Democratic Republic of the Congo",
                   "fifa_code": "COD", "iso2": "CD"},
            "13": {"id": "13", "name_en": "United States",
                   "fifa_code": "USA", "iso2": "US"},
        }
        m = build_team_id_map(teams, countries=countries)
        # ICS "DR Congo" → 42 via code_fifa bridge
        assert m["DR Congo"] == "42"
        # ICS "USA" → 13 via code_fifa (this is also covered by pass 2,
        # but pass 5 is a redundant safety net)
        assert m["USA"] == "13"

    def test_countries_reverse_lookup_does_not_override(self):
        """If a key is already in the map from an earlier pass, countries
        pass does NOT overwrite it (priority: API > countries)."""
        countries = {"Fake Name": {"code_iso": "ca", "code_fifa": "CAN"}}
        teams = {
            "5": {"id": "5", "name_en": "Canada",
                  "fifa_code": "CAN", "iso2": "CA"},
        }
        m = build_team_id_map(teams, countries=countries)
        # "Canada" from pass 1 wins; "Fake Name" from countries is a NEW key
        assert m["Canada"] == "5"
        assert m["Fake Name"] == "5"  # also added (but lower priority)

    def test_countries_none_disables_pass5(self):
        """If countries=None (default), the resolver still works for
        &-style and direct name matches — just not abbreviations."""
        m = build_team_id_map(self._sample_teams())  # no countries
        # Bosnia & Herzegovina still resolves via pass 4 normalize
        assert m[_norm_team_key("Bosnia & Herzegovina")] == "6"
        # But abbreviation case (not tested here) would need countries

    def test_real_data_bosnia_bug_resolved(self):
        """End-to-end: real B-group situation. With the resolver, all
        4 final matches resolve, and standings has 4 teams."""
        from src.data.ics_parser import parse_ics
        from src.data.ics_fetcher import fetch_ics
        from src.data.countries import enrich_matches as enrich_countries
        from src.data.details import enrich_matches as enrich_details, load_details
        from src.data.worldcup_api import get_teams_by_id

        matches = parse_ics(fetch_ics(force=False))
        enrich_countries(matches)
        enrich_details(matches)
        b_matches = [m for m in matches if (m.get("group") or "").upper() == "B"]
        # Sanity: 6 group matches, 4 are final in details
        finals = [m for m in b_matches
                  if (m.get("details") or {}).get("status") == "final"]
        assert len(finals) == 4

        # Without resolver (old name_to_id): B group standings = 3 teams
        teams = get_teams_by_id()
        old_name_to_id = {}
        for tid, t in teams.items():
            for k in (t.get("name_en"), t.get("fifa_code")):
                if k:
                    old_name_to_id[str(k)] = str(tid)
        old = compute_standings_from_details(
            "B", load_details(), b_matches, old_name_to_id,
        ) or []
        # Old behavior: only 3 teams (Bosnia dropped)
        assert len(old) == 3
        old_ids = {t["team_id"] for t in old}
        assert "6" not in old_ids  # Bosnia's team_id, missing

        # With resolver: B group standings = 4 teams
        new_name_to_id = build_team_id_map(teams)
        new = compute_standings_from_details(
            "B", load_details(), b_matches, new_name_to_id,
        ) or []
        assert len(new) == 4
        new_ids = {t["team_id"] for t in new}
        assert "6" in new_ids  # Bosnia's team_id, now present

        # Sanity check: Canada still 1W (vs Qatar 6-0), still 1D (vs Bosnia 1-1)
        canada = next(t for t in new if t["team_id"] == "5")
        assert canada["mp"] == 2
        assert canada["w"] == 1
        assert canada["d"] == 1
        assert canada["gf"] == 7  # 6 (vs Qatar) + 1 (vs Bosnia)
        assert canada["ga"] == 1
        assert canada["pts"] == 4

        # Switzerland: 1W (vs Bosnia 4-1), 0D 1L (vs Qatar 1-1 → that was Qatar 1-1 Switzerland)
        # Wait — re-check: 6/13 Qatar 1-1 Switzerland (home=Qatar, away=Switzerland)
        # So Switzerland drew away → 1D. 6/19 Switzerland 4-1 Bosnia (home=Switzerland)
        # → 1W. Total: 1W 1D 0L.
        switzerland = next(t for t in new if t["team_id"] == "8")
        assert switzerland["mp"] == 2
        assert switzerland["w"] == 1
        assert switzerland["d"] == 1
        assert switzerland["gf"] == 5  # 1 (vs Qatar) + 4 (vs Bosnia)
        assert switzerland["ga"] == 2  # 1 (vs Qatar) + 1 (vs Bosnia)
        assert switzerland["pts"] == 4  # 3 + 1
        # (Note: canada and switzerland tie on 4 PTS; sort by GD: canada +6, switzerland +3)
        # So canada should be ranked higher.
        new_sorted_ids = [t["team_id"] for t in new]
        assert new_sorted_ids.index("5") < new_sorted_ids.index("8")

        # Bosnia: 1D (vs Canada 1-1) 1L (vs Switzerland 1-4) → 0W 1D 1L GF=2 GA=5
        bosnia = next(t for t in new if t["team_id"] == "6")
        assert bosnia["mp"] == 2
        assert bosnia["w"] == 0
        assert bosnia["d"] == 1
        assert bosnia["l"] == 1
        assert bosnia["gf"] == 2
        assert bosnia["ga"] == 5
        assert bosnia["pts"] == 1

    def test_real_data_k_group_dr_congo_bug_resolved(self):
        """Real K-group situation: 'DR Congo' (ICS) cannot be derived
        from 'Democratic Republic of the Congo' (API) by character
        normalization alone — needs countries.json reverse lookup."""
        from src.data.ics_parser import parse_ics
        from src.data.ics_fetcher import fetch_ics
        from src.data.countries import enrich_matches as enrich_countries
        from src.data.countries import all_countries
        from src.data.details import enrich_matches as enrich_details, load_details
        from src.data.worldcup_api import get_teams_by_id

        matches = parse_ics(fetch_ics(force=False))
        enrich_countries(matches)
        enrich_details(matches)
        k_matches = [m for m in matches if (m.get("group") or "").upper() == "K"]
        finals = [m for m in k_matches
                  if (m.get("details") or {}).get("status") == "final"]
        assert len(finals) == 2

        teams = get_teams_by_id()
        # Without countries: only 2 teams (DR Congo dropped, so 6/17
        # Portugal 1-1 DR Congo match is silently skipped)
        no_countries = build_team_id_map(teams)
        old = compute_standings_from_details(
            "K", load_details(), k_matches, no_countries,
        ) or []
        # Note: this depends on whether other K-group names resolve.
        # Old behavior: Portugal also might drop if its name mapping
        # is missing. The crucial assertion is the "with countries" case.

        # With countries: 4 teams (DR Congo and Portugal both present)
        with_countries = build_team_id_map(teams, countries=all_countries())
        new = compute_standings_from_details(
            "K", load_details(), k_matches, with_countries,
        ) or []
        assert len(new) == 4
        new_ids = {t["team_id"] for t in new}
        # DR Congo's team_id is 42
        assert "42" in new_ids
        # Portugal's team_id is 41
        assert "41" in new_ids

