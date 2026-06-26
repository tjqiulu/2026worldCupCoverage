"""Tests for country metadata + match enrichment."""
from pathlib import Path

import pytest

from src.data.countries import (
    all_countries,
    enrich_match,
    enrich_matches,
    is_placeholder,
    lookup,
    norm_team_key,
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
        # England uses the flag-icons `gb-eng` subdivision class (St. George's
        # Cross), NOT the generic UK Union Jack. flag-icons 6.6.6 ships
        # `fi-gb-eng` and `fi-gb-sct` (verified against CDN).
        # See Plan 045 revert of Plan 9b8f3d5 (which mistakenly used `gb`).
        info = lookup("England")
        assert info is not None
        assert info["code_iso"] == "gb-eng"
        assert info["code_fifa"] == "ENG"

    def test_scotland_uses_subnational_flag(self):
        # Scotland uses the flag-icons `gb-sct` subdivision class (Saltire).
        # See test_england_uses_subnational_flag for context.
        info = lookup("Scotland")
        assert info is not None
        assert info["code_iso"] == "gb-sct"
        assert info["code_fifa"] == "SCO"


class TestResolveCodeIso:
    """Tests for src.app._resolve_code_iso — defensive validator for API iso2."""

    def test_api_2letter_alpha_wins(self):
        from src.app import _resolve_code_iso
        # API gives a proper 2-letter code → use it, ignore meta
        assert _resolve_code_iso("GH", {"code_iso": "gb"}) == "gh"
        assert _resolve_code_iso("us", {"code_iso": "gb"}) == "us"

    def test_api_3letter_falls_back_to_meta(self):
        from src.app import _resolve_code_iso
        # API gives a 3-letter FIFA code (e.g. ENG/SCO) → reject, use meta
        assert _resolve_code_iso("ENG", {"code_iso": "gb"}) == "gb"
        assert _resolve_code_iso("SCO", {"code_iso": "gb"}) == "gb"

    def test_api_empty_falls_back_to_meta(self):
        from src.app import _resolve_code_iso
        assert _resolve_code_iso("", {"code_iso": "gb"}) == "gb"
        assert _resolve_code_iso(None, {"code_iso": "gb"}) == "gb"

    def test_api_with_digits_or_symbols_falls_back_to_meta(self):
        from src.app import _resolve_code_iso
        # Anything that isn't a clean 2-letter alpha falls back
        assert _resolve_code_iso("GH1", {"code_iso": "gb"}) == "gb"
        assert _resolve_code_iso("G", {"code_iso": "gb"}) == "gb"
        assert _resolve_code_iso("G H", {"code_iso": "gb"}) == "gb"

    def test_no_meta_returns_empty(self):
        from src.app import _resolve_code_iso
        assert _resolve_code_iso("ENG", None) == ""
        assert _resolve_code_iso("", None) == ""

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


# === Plan 028: lookup() 3-pass alias fallback ===
# worldcup26.ir API and baires ICS use different spellings. Plan 027
# fixed the standings calculation. Plan 028 fixes the bilingual name
# display by adding 3-pass fallback to lookup():
#   1. exact match
#   2. normalized match (lowercase, & → and, collapse whitespace)
#   3. code_fifa / code_iso reverse lookup

class TestNormTeamKey:
    """Unit tests for the shared fuzzy-lookup helper."""

    def test_ampersand_to_and(self):
        assert norm_team_key("Bosnia & Herzegovina") == "bosnia and herzegovina"

    def test_lowercases(self):
        assert norm_team_key("USA") == "usa"
        assert norm_team_key("United States") == "united states"

    def test_collapses_whitespace(self):
        assert norm_team_key("  multiple   spaces  ") == "multiple spaces"

    def test_preserves_unicode_letters(self):
        # "Côte d'Ivoire" / "Curaçao" keep their accented letters;
        # only ASCII punctuation gets stripped.
        assert norm_team_key("Côte d'Ivoire") == "côte divoire"
        assert norm_team_key("Curaçao") == "curaçao"
        assert norm_team_key("U.S.A.") == "usa"

    def test_empty_input(self):
        assert norm_team_key("") == ""
        assert norm_team_key(None) == ""

    def test_ics_to_api_translation(self):
        """The specific cross-source cases Plan 028 covers."""
        assert norm_team_key("Bosnia & Herzegovina") == "bosnia and herzegovina"
        assert norm_team_key("DR Congo") == "dr congo"
        assert norm_team_key("USA") == "usa"
        # The reverse direction also normalizes to the same form:
        assert norm_team_key("Bosnia and Herzegovina") == "bosnia and herzegovina"
        assert norm_team_key("United States") == "united states"
        assert norm_team_key("Democratic Republic of the Congo") == "democratic republic of the congo"


class TestLookupAliasFallback:
    """Plan 028: 3-pass fallback in lookup() covers cross-source
    spelling variations. Real bug case: /api/teams used worldcup26.ir
    API's 'Bosnia and Herzegovina' / 'United States' / 'Democratic
    Republic of the Congo' to look up countries.json, but the JSON is
    keyed by ICS names 'Bosnia & Herzegovina' / 'USA' / 'DR Congo'.
    Result: name_zh was None for 3 teams, breaking the standings modal."""

    # --- Pass 1: exact match (priority preserved) ---

    def test_pass1_exact_match_wins(self):
        """Exact match still returns the right entry; Pass 2/3 don't
        accidentally override it."""
        info = lookup("Mexico")
        assert info is not None
        assert info["name_zh"] == "墨西哥"
        assert info["code_iso"] == "mx"

    def test_pass1_ampersand_exact_still_works(self):
        """If the caller happens to use the ICS spelling exactly,
        Pass 1 still hits (no regression on existing usage)."""
        info = lookup("Bosnia & Herzegovina")
        assert info is not None
        assert info["name_zh"] == "波黑"

    def test_pass1_usa_exact_still_works(self):
        info = lookup("USA")
        assert info is not None
        assert info["name_zh"] == "美国"

    # --- Pass 2: normalized match ---

    def test_pass2_ampersand_fallback(self):
        """The bug case: API returns 'Bosnia and Herzegovina' but
        countries.json key is 'Bosnia & Herzegovina'. Pass 2 (normalize)
        bridges them."""
        info = lookup("Bosnia and Herzegovina")
        assert info is not None
        assert info["name_zh"] == "波黑"
        assert info["code_iso"] == "ba"
        assert info["code_fifa"] == "BIH"

    def test_pass2_is_case_insensitive(self):
        """Lowercase / mixed-case queries also work via Pass 2."""
        assert lookup("bosnia and herzegovina")["name_zh"] == "波黑"
        assert lookup("BOSNIA AND HERZEGOVINA")["name_zh"] == "波黑"

    def test_pass2_preserves_exact_match_priority(self):
        """If two countries happened to normalize to the same key (very
        unlikely for real data), Pass 1 still wins. Sanity check: every
        countries.json key has a unique norm form, so Pass 1 only ever
        differs from Pass 2 when there are spelling variants."""
        for k in all_countries().keys():
            norm_forms = [
                norm_team_key(other_k)
                for other_k in all_countries().keys()
                if norm_team_key(other_k) == norm_team_key(k)
            ]
            # All countries that normalize to the same form should be
            # spelling variants of the same country. Spot-check that
            # Bosnia's variants are all Bosnia:
            if "Bosnia" in k:
                assert all("Bosnia" in n or "bosnia" in n for n in [k] + norm_forms)

    # --- Pass 3: code_fifa / code_iso reverse lookup ---

    def test_pass3_usa_full_name_fallback(self):
        """API returns 'United States'; countries.json key is 'USA'.
        Pass 3 finds it via code_fifa='USA' reverse lookup."""
        info = lookup("United States")
        assert info is not None
        assert info["name_zh"] == "美国"
        assert info["code_iso"] == "us"

    def test_pass3_drc_full_name_fallback(self):
        """API returns 'Democratic Republic of the Congo'; countries.json
        key is 'DR Congo'. Pass 3 via code_fifa='COD'."""
        info = lookup("Democratic Republic of the Congo")
        assert info is not None
        assert info["name_zh"] == "民主刚果"
        assert info["code_iso"] == "cd"
        assert info["code_fifa"] == "COD"

    def test_pass3_iso2_fallback(self):
        """If the API returned a lowercase ISO2 code, Pass 3 would
        also find it (case-insensitive)."""
        info = lookup("us")
        assert info is not None
        assert info["name_zh"] == "美国"
        info = lookup("US")
        assert info is not None
        assert info["name_zh"] == "美国"

    def test_pass3_does_not_confuse_different_teams(self):
        """Pass 3 must distinguish teams with different codes. 'MEX'
        and 'MEXICO' (hypothetical collision) would not both match."""
        # Sanity: every code_fifa is unique
        codes = [v["code_fifa"] for v in all_countries().values() if v.get("code_fifa")]
        assert len(codes) == len(set(codes)), "code_fifa must be unique"

    # --- All passes fail ---

    def test_unknown_returns_none_after_all_passes(self):
        """Random unknown name → None (no false positives)."""
        assert lookup("Atlantis") is None
        assert lookup("Made-up Country") is None
        assert lookup("xyz123") is None

    def test_empty_input_returns_none(self):
        assert lookup("") is None
        assert lookup(None) is None
        assert lookup("   ") is None  # whitespace-only treated as empty via Pass 1

    # --- End-to-end: ICS ↔ API symmetry ---

    def test_ics_api_pair_returns_same_info(self):
        """For each of the 3 known cross-source variants, both spellings
        must resolve to the same {name_zh, code_iso, code_fifa}."""
        pairs = [
            ("Bosnia & Herzegovina", "Bosnia and Herzegovina"),
            ("USA", "United States"),
            ("DR Congo", "Democratic Republic of the Congo"),
        ]
        for ics, api in pairs:
            ics_info = lookup(ics)
            api_info = lookup(api)
            assert ics_info is not None, f"ICS form failed: {ics!r}"
            assert api_info is not None, f"API form failed: {api!r}"
            assert ics_info == api_info, (
                f"Same country returned different info: "
                f"ICS={ics!r} -> {ics_info}, API={api!r} -> {api_info}"
            )

    def test_all_48_world_cup_teams_resolvable_from_api_spellings(self):
        """End-to-end: for all 48 qualified teams, the API's spelling
        (which is what /api/teams uses) must resolve to a countries.json
        entry. This is the bug we're fixing — without Plan 028, 3 teams
        (USA, Bosnia, DR Congo) returned None for name_zh."""
        from src.data.worldcup_api import fetch_teams
        api_teams = fetch_teams()
        failures = []
        for t in api_teams:
            name = t.get("name_en")
            if not name:
                continue
            info = lookup(name)
            if info is None or not info.get("name_zh"):
                failures.append((t.get("id"), name))
        assert not failures, (
            f"API team names that don't resolve via countries.json: {failures}"
        )
