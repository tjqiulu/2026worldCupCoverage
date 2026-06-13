"""Tests for worldcup26.ir API integration (Plan 012)."""
import json
from unittest.mock import patch, MagicMock

import pytest

from src.data.worldcup_api import (
    clear_cache,
    find_match_id,
    game_to_details_entry,
    last_fetch_age_seconds,
    parse_scorers,
    _to_int,
)


# === Test data ===

RAW_FANCY_QUOTES = "{J. Quiñones 9\u0027,R. Jiménez 67\u0027}"
RAW_JSON_ARRAY = "{\"I.B. Hwang 67\u0027\",\"H.G. Oh 80\u0027\"}"
RAW_SINGLE = "{\"L. Krejčí 59\u0027\"}"


# === parse_scorers ===

class TestParseScorers:
    def test_fancy_quotes_no_json(self):
        # API format: {Player1 9',Player2 67'} (no JSON quotes)
        result = parse_scorers(RAW_FANCY_QUOTES)
        assert result == [
            {"player": "J. Quiñones", "minute": 9},
            {"player": "R. Jiménez", "minute": 67},
        ]

    def test_proper_json_array(self):
        result = parse_scorers(RAW_JSON_ARRAY)
        assert result == [
            {"player": "I.B. Hwang", "minute": 67, "stoppage": None, "type": None},
            {"player": "H.G. Oh", "minute": 80, "stoppage": None, "type": None},
        ]

    def test_single_json_item(self):
        result = parse_scorers(RAW_SINGLE)
        assert result == [{"player": "L. Krejčí", "minute": 59, "stoppage": None, "type": None}]

    @pytest.mark.parametrize("raw", ["null", "NULL", "", "{}"])
    def test_empty(self, raw):
        assert parse_scorers(raw) == []

    def test_unicode_fancy_quotes_normalized(self):
        # Use actual Unicode chars (U+201C, U+201D)
        raw = '{\u201cJ. Smith 10\u201d}'
        result = parse_scorers(raw)
        assert result == [{"player": "J. Smith", "minute": 10, "stoppage": None, "type": None}]


# === _to_int ===

class TestToInt:
    @pytest.mark.parametrize("value,expected", [
        ("2", 2),
        ("0", 0),
        (0, 0),
        (None, 0),
        ("null", 0),
        ("NULL", 0),
        ("", 0),
        ("abc", 0),  # malformed → 0
    ])
    def test_conversion(self, value, expected):
        assert _to_int(value) == expected


# === game_to_details_entry ===

class TestGameToDetailsEntry:
    def test_unfinished_game_returns_none(self):
        game = {"finished": "FALSE", "home_score": "0", "away_score": "0"}
        assert game_to_details_entry(game) is None

    def test_finished_game_with_scores(self):
        game = {
            "finished": "TRUE",
            "home_score": "2",
            "away_score": "0",
            "home_scorers": RAW_FANCY_QUOTES,
            "away_scorers": "null",
        }
        entry = game_to_details_entry(game)
        assert entry is not None
        assert entry["status"] == "final"
        assert entry["score"] == {"home": 2, "away": 0}
        assert len(entry["goalscorers"]) == 2
        assert entry["goalscorers"][0]["team"] == "home"
        assert entry["goalscorers"][0]["player"] == "J. Quiñones"
        assert entry["goalscorers"][0]["minute"] == 9


# === find_match_id ===

class TestFindMatchId:
    def test_match_by_team_names(self):
        matches = [
            {"match_id": "m1", "home": {"name": "Mexico"}, "away": {"name": "South Africa"}},
            {"match_id": "m2", "home": {"name": "South Korea"}, "away": {"name": "Czech Republic"}},
        ]
        game = {"home_team_name_en": "Mexico", "away_team_name_en": "South Africa"}
        assert find_match_id(game, matches) == "m1"

    def test_no_match_returns_none(self):
        matches = [{"match_id": "m1", "home": {"name": "Brazil"}, "away": {"name": "Argentina"}}]
        game = {"home_team_name_en": "Mexico", "away_team_name_en": "South Africa"}
        assert find_match_id(game, matches) is None

    def test_empty_names_returns_none(self):
        assert find_match_id({"home_team_name_en": "", "away_team_name_en": ""}, []) is None

    def test_swap_does_not_match(self):
        """Reversed home/away should NOT match (exact order matters)."""
        matches = [{"match_id": "m1", "home": {"name": "Mexico"}, "away": {"name": "South Africa"}}]
        game = {"home_team_name_en": "South Africa", "away_team_name_en": "Mexico"}
        assert find_match_id(game, matches) is None


# === merge_from_api ===

class TestMergeFromApi:
    def test_existing_entry_not_overwritten(self):
        from src.data.details import merge_from_api
        existing = {
            "m1": {"status": "final", "score": {"home": 99, "away": 99}, "note": "manual"},
        }
        api = {"m1": {"status": "final", "score": {"home": 2, "away": 0}}}
        merged, added = merge_from_api(existing, api)
        assert merged["m1"]["score"] == {"home": 99, "away": 99}  # existing wins
        assert "note" in merged["m1"]
        assert added == 0

    def test_new_entry_added(self):
        from src.data.details import merge_from_api
        existing = {"m1": {"status": "final"}}
        api = {"m2": {"status": "final", "score": {"home": 1, "away": 0}}}
        merged, added = merge_from_api(existing, api)
        assert "m2" in merged
        assert merged["m2"]["score"] == {"home": 1, "away": 0}
        assert added == 1


# === clear_cache ===

class TestClearCache:
    def test_clear(self):
        clear_cache()
        assert last_fetch_age_seconds() is None


# === fetch_details_for_matches (end-to-end with real API) ===
# Note: this hits the real worldcup26.ir API. If offline, will return empty.

class TestFetchEndToEnd:
    def test_fetches_known_matches(self):
        import json
        from src.data.worldcup_api import fetch_details_for_matches, clear_cache
        clear_cache()
        matches = json.loads(open("data/matches.json").read())
        result = fetch_details_for_matches(matches)
        # As of test time, the API should have at least 2 finished matches
        if len(result) == 0:
            pytest.skip("API returned no finished matches (offline or no data yet)")
        # MEX vs RSA
        assert any("MEX" in str(m) for m in matches) or any(
            m["home"]["name"] == "Mexico" for m in matches
        )
        # Each result entry should have status, score, goalscorers
        for mid, entry in result.items():
            assert entry["status"] == "final"
            assert "score" in entry
            assert "goalscorers" in entry


# === Plan 015: Stadiums, Groups, Teams lookups ===

class TestStadiums:
    """Tests for fetch_stadiums + find_stadium_by_city."""

    def test_fetch_stadiums_returns_list(self):
        from src.data.worldcup_api import fetch_stadiums, clear_cache
        clear_cache()
        stadiums = fetch_stadiums()
        if not stadiums:
            pytest.skip("No stadiums returned (offline or API down)")
        # At least 16 stadiums for WC 2026
        assert len(stadiums) >= 16
        for s in stadiums[:3]:
            assert "id" in s
            assert "name_en" in s
            assert "city_en" in s
            assert "capacity" in s and s["capacity"] > 0

    def test_find_stadium_by_city_exact(self):
        from src.data.worldcup_api import find_stadium_by_city, clear_cache
        clear_cache()
        s = find_stadium_by_city("Mexico City")
        if s is None:
            pytest.skip("API offline")
        assert s["city_en"].lower() == "mexico city"
        assert s["capacity"] > 0

    def test_find_stadium_by_city_with_paren(self):
        """ICS venue is e.g., 'Boston (Foxborough)' — should still match."""
        from src.data.worldcup_api import find_stadium_by_city, clear_cache
        clear_cache()
        s = find_stadium_by_city("Boston (Foxborough)")
        if s is None:
            pytest.skip("API offline or city not found")
        # Should match a stadium whose city is "Boston" (or contains "boston")
        assert "boston" in s["city_en"].lower()

    def test_find_stadium_by_city_empty(self):
        from src.data.worldcup_api import find_stadium_by_city
        assert find_stadium_by_city("") is None
        assert find_stadium_by_city(None) is None

    def test_find_stadium_by_city_no_match(self):
        from src.data.worldcup_api import find_stadium_by_city
        assert find_stadium_by_city("Atlantis") is None


class TestGroups:
    """Tests for fetch_groups + find_group_standings."""

    def test_fetch_groups_returns_list(self):
        from src.data.worldcup_api import fetch_groups, clear_cache
        clear_cache()
        groups = fetch_groups()
        if not groups:
            pytest.skip("API offline")
        # 12 groups A-L
        assert len(groups) >= 12
        for g in groups[:3]:
            assert "name" in g
            assert "teams" in g
            assert len(g["teams"]) == 4  # 4 teams per group

    def test_find_group_standings_returns_sorted(self):
        from src.data.worldcup_api import find_group_standings, clear_cache
        clear_cache()
        standings = find_group_standings("A")
        if standings is None:
            pytest.skip("API offline")
        assert len(standings) == 4
        # Sorted by pts desc
        for i in range(len(standings) - 1):
            cur = int(standings[i].get("pts", 0) or 0)
            nxt = int(standings[i + 1].get("pts", 0) or 0)
            assert cur >= nxt, f"Standings not sorted: {cur} < {nxt}"

    def test_find_group_standings_empty(self):
        from src.data.worldcup_api import find_group_standings
        assert find_group_standings("") is None
        assert find_group_standings(None) is None
        assert find_group_standings("Z") is None  # not a real group


class TestTeams:
    """Tests for fetch_teams + get_teams_by_id."""

    def test_get_teams_by_id_returns_map(self):
        from src.data.worldcup_api import get_teams_by_id, clear_cache
        clear_cache()
        teams = get_teams_by_id()
        if not teams:
            pytest.skip("API offline")
        # 48 group-stage teams
        assert len(teams) == 48
        # Each team has id-keyed entry with name_en, iso2
        for tid, t in list(teams.items())[:3]:
            assert t.get("name_en")
            assert t.get("iso2")
            assert t.get("fifa_code")


# === Plan 016: Team name normalization (Plan 016 fix) ===
# ICS uses different team names than worldcup26.ir. Without normalization,
# some finished matches don't get their scores (e.g., "Bosnia & Herzegovina"
# vs "Bosnia and Herzegovina" — user reported "待更新" bug 2026-06-13).

class TestTeamNameNormalization:
    def test_bosnia_ampersand_vs_and(self):
        from src.data.worldcup_api import find_match_id
        api_game = {
            "home_team_name_en": "Canada",
            "away_team_name_en": "Bosnia and Herzegovina",  # API style
        }
        our_matches = [{
            "match_id": "test-can-bih",
            "home": {"name": "Canada"},
            "away": {"name": "Bosnia & Herzegovina"},  # ICS style
        }]
        result = find_match_id(api_game, our_matches)
        assert result == "test-can-bih", f"Expected match, got {result}"

    def test_usa_vs_united_states(self):
        from src.data.worldcup_api import find_match_id
        api_game = {
            "home_team_name_en": "United States",
            "away_team_name_en": "Paraguay",
        }
        our_matches = [{
            "match_id": "test-usa-par",
            "home": {"name": "USA"},  # ICS uses abbreviation
            "away": {"name": "Paraguay"},
        }]
        result = find_match_id(api_game, our_matches)
        assert result == "test-usa-par"

    def test_dr_congo_alias(self):
        from src.data.worldcup_api import find_match_id
        api_game = {
            "home_team_name_en": "Democratic Republic of the Congo",
            "away_team_name_en": "Portugal",
        }
        our_matches = [{
            "match_id": "test-cgo-por",
            "home": {"name": "DR Congo"},  # ICS abbreviation
            "away": {"name": "Portugal"},
        }]
        result = find_match_id(api_game, our_matches)
        assert result == "test-cgo-por"

    def test_exact_match_still_works(self):
        """The fallback shouldn't break exact matches."""
        from src.data.worldcup_api import find_match_id
        api_game = {
            "home_team_name_en": "Mexico",
            "away_team_name_en": "South Africa",
        }
        our_matches = [{
            "match_id": "test-mex-rsa",
            "home": {"name": "Mexico"},
            "away": {"name": "South Africa"},
        }]
        result = find_match_id(api_game, our_matches)
        assert result == "test-mex-rsa"

    def test_no_match_returns_none(self):
        from src.data.worldcup_api import find_match_id
        api_game = {
            "home_team_name_en": "Atlantis",
            "away_team_name_en": "El Dorado",
        }
        our_matches = [{
            "match_id": "test",
            "home": {"name": "Mexico"},
            "away": {"name": "Brazil"},
        }]
        result = find_match_id(api_game, our_matches)
        assert result is None

    def test_real_canada_bosnia_md1_now_matches(self):
        """The original user complaint — end-to-end."""
        from src.data.worldcup_api import find_match_id
        # Get the real Canada-Bosnia MD1 game from API
        games = [{g["home_team_name_en"]: g["away_team_name_en"], "data": g}
                 for g in _fetch_real_games() if g.get("home_team_name_en") == "Canada" and "Bosnia" in (g.get("away_team_name_en") or "")]
        assert len(games) >= 1, "Canada-Bosnia game not in API"
        # Use the first one as API game
        api_game = {"home_team_name_en": "Canada", "away_team_name_en": "Bosnia and Herzegovina"}
        # Load our matches
        import json
        our_matches = json.loads(open("data/matches.json").read())
        result = find_match_id(api_game, our_matches)
        assert result is not None, "Should match via normalized name"


def _fetch_real_games():
    """Helper: real API games for end-to-end tests."""
    from src.data.worldcup_api import _fetch_raw, clear_cache
    clear_cache()
    return _fetch_raw()


# === Plan 016: Stoppage time + own goal parser (the real bug) ===
# User reported: USA 4-1 Paraguay modal showed all stoppage-time goals as 0'
# and own goal's player name as "D. Bobadilla 7'(OG)"

class TestScorerStringParser:
    """Tests for _parse_scorer_strings — handles minute + optional stoppage + optional type suffix."""

    def test_simple_minute(self):
        from src.data.worldcup_api import _parse_scorer_strings
        result = _parse_scorer_strings(["F. Balogun 31'"])
        assert result == [{"player": "F. Balogun", "minute": 31, "stoppage": None, "type": None}]

    def test_minute_with_stoppage_45_plus_5(self):
        from src.data.worldcup_api import _parse_scorer_strings
        result = _parse_scorer_strings(["F. Balogun 45'+5'"])
        assert result == [{"player": "F. Balogun", "minute": 45, "stoppage": 5, "type": None}]

    def test_minute_with_stoppage_90_plus_8(self):
        from src.data.worldcup_api import _parse_scorer_strings
        result = _parse_scorer_strings(["G. Reyna 90'+8'"])
        assert result == [{"player": "G. Reyna", "minute": 90, "stoppage": 8, "type": None}]

    def test_own_goal_suffix(self):
        from src.data.worldcup_api import _parse_scorer_strings
        result = _parse_scorer_strings(["D. Bobadilla 7'(OG)"])
        assert result == [{"player": "D. Bobadilla", "minute": 7, "stoppage": None, "type": "own_goal"}]

    def test_penalty_suffix(self):
        from src.data.worldcup_api import _parse_scorer_strings
        result = _parse_scorer_strings(["Player 50'(P)"])
        assert result[0]["type"] == "penalty"
        assert result[0]["minute"] == 50

    def test_real_usa_paraguay_full(self):
        """The exact data from the user's bug report."""
        from src.data.worldcup_api import _parse_scorer_strings
        raw = '{"D. Bobadilla 7\'(OG)","F. Balogun 31\'","F. Balogun 45\'+5\'","G. Reyna 90\'+8\'"}'
        # Strip outer braces, wrap as list
        s = raw[1:-1]
        import json
        arr = json.loads(f"[{s}]")
        result = _parse_scorer_strings(arr)
        assert len(result) == 4
        assert result[0] == {"player": "D. Bobadilla", "minute": 7, "stoppage": None, "type": "own_goal"}
        assert result[1] == {"player": "F. Balogun", "minute": 31, "stoppage": None, "type": None}
        assert result[2] == {"player": "F. Balogun", "minute": 45, "stoppage": 5, "type": None}
        assert result[3] == {"player": "G. Reyna", "minute": 90, "stoppage": 8, "type": None}

    def test_unparseable_returns_minute_zero(self):
        """Items that don't match any pattern still get added with minute=0."""
        from src.data.worldcup_api import _parse_scorer_strings
        result = _parse_scorer_strings(["some weird name"])
        assert result == [{"player": "some weird name", "minute": 0, "stoppage": None, "type": None}]


class TestSaveDetailsInvalidatesCache:
    """Plan 016 fix: save_details() must invalidate _load() lru_cache so subsequent
    /api/matches requests see the newly-saved data (previously the cache held stale data)."""

    def test_cache_invalidated_on_save(self, tmp_path, monkeypatch):
        import json
        from src.data import details
        # Point DETAILS_FILE at a temp file
        test_file = tmp_path / "details.json"
        test_file.write_text(json.dumps({"mid1": {
            "status": "final", "score": {"home": 1, "away": 0},
            "goalscorers": [{"team": "home", "player": "A", "minute": 10, "stoppage": None, "type": None}]
        }}))
        monkeypatch.setattr(details, "DETAILS_FILE", test_file)
        # First read populates cache
        details._load.cache_clear()
        d1 = details._load()
        assert "mid1" in d1
        # Modify file on disk
        test_file.write_text(json.dumps({"mid2": {
            "status": "final", "score": {"home": 2, "away": 0},
            "goalscorers": []
        }}))
        # Without invalidation, _load would return cached
        d_pre = details._load()
        assert "mid2" not in d_pre, "lru_cache is hiding the new entry (this is the bug)"
        # Now save_details should clear the cache
        details.save_details({"mid2": {"status": "final", "score": {"home": 2, "away": 0}, "goalscorers": []}})
        d_post = details._load()
        assert "mid2" in d_post, "save_details should have invalidated the cache"


class TestValidatorHandlesNullType:
    """Plan 016 fix: validate_entry must accept type=null (not 'malformed')."""

    def test_goalscorer_with_null_type_is_valid(self):
        from src.data.details import validate_entry
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"team": "home", "player": "Test", "minute": 10, "stoppage": None, "type": None}
            ],
        }
        assert validate_entry(entry) is True

    def test_goalscorer_without_type_field_is_valid(self):
        """Backward compat: old data without explicit type=null should still work."""
        from src.data.details import validate_entry
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"team": "home", "player": "Test", "minute": 10}
            ],
        }
        assert validate_entry(entry) is True

    def test_goalscorer_with_invalid_type_is_invalid(self):
        from src.data.details import validate_entry
        entry = {
            "status": "final",
            "score": {"home": 1, "away": 0},
            "goalscorers": [
                {"team": "home", "player": "Test", "minute": 10, "type": "weird"}
            ],
        }
        assert validate_entry(entry) is False
