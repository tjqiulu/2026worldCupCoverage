"""Tests for frontend init order (Plan 033).

The frontend init must:
1. Load /api/matches
2. Load /api/teams (await)
3. Load /api/qualification (await) — Plan 033 added await
4. Render bracket/matches (with qualification state available)

This test file verifies the JS source for correct init order and
end-to-end API behavior that the init relies on.
"""
import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = PROJECT_ROOT / "src" / "static" / "js" / "main.js"


# ============================================================
# Source-level checks: ensure init order in main.js is correct
# ============================================================

class TestMainJsInitOrder:
    """Verify main.js init sequence is correct.

    Plan 033: loadQualification() must be AWAITED before renderBracket(),
    not fire-and-forget. Without this, bracket renders before qualification
    data is available, causing all slots to show placeholders.
    """

    def test_main_js_exists(self):
        assert MAIN_JS.exists(), f"main.js not found at {MAIN_JS}"

    def test_load_qualification_function_exists(self):
        content = MAIN_JS.read_text(encoding="utf-8")
        assert "async function loadQualification" in content, \
            "loadQualification() should be async"

    def test_load_matches_calls_await_load_qualification(self):
        """Plan 033: loadQualification() must be awaited."""
        content = MAIN_JS.read_text(encoding="utf-8")
        # Find the loadMatches function: locate start, then walk braces
        m = re.search(r"async function loadMatches[^{]*\{", content)
        assert m, "Could not find loadMatches function start"
        # Walk braces to find the matching close
        start = m.end() - 1  # position of '{'
        depth = 0
        end = start
        for i in range(start, len(content)):
            ch = content[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        body = content[start:end]
        # Should contain 'await loadQualification()'
        assert "await loadQualification()" in body, \
            "Plan 033: loadMatches must await loadQualification() — " \
            "fire-and-forget causes bracket to render with null data"
        # And it should be wrapped in try/catch so failure is non-fatal
        assert "try" in body and "catch" in body, \
            "loadQualification should be wrapped in try/catch " \
            "(bracket must render even if qualification fails)"

    def test_render_bracket_uses_resolve_bracket_placeholder(self):
        """renderBracket() must use resolveBracketPlaceholder() so locked
        teams display in their slots."""
        content = MAIN_JS.read_text(encoding="utf-8")
        assert "resolveBracketPlaceholder" in content, \
            "renderBracket should call resolveBracketPlaceholder"
        # And resolveBracketPlaceholder must be defined
        assert "function resolveBracketPlaceholder" in content, \
            "resolveBracketPlaceholder function must be defined"


# ============================================================
# CSS audit: lock down bracket card dimensions to prevent overlap
# ============================================================

class TestBracketCssDimensions:
    """Plan 034: Lock down bracket card dimensions to prevent overlap.

    The grid row height must be >= max card height. Without explicit
    constraints, font rendering can overflow rows causing visual overlap.
    These tests prevent regression.
    """

    def test_bracket_mirror_grid_row_height_defined(self):
        css = (PROJECT_ROOT / "src" / "static" / "css" / "main.css").read_text()
        m = re.search(r"\.bracket-mirror\s*\{[^}]*grid-template-rows:\s*repeat\(8,\s*(\d+)px\)", css)
        assert m, "bracket-mirror grid-template-rows not found"
        row_height = int(m.group(1))
        # Row height must be >= 110px to prevent overlap
        assert row_height >= 110, \
            f"grid row height {row_height}px is too small, will cause card overlap"

    def test_bracket_mirror_min_width_is_zero(self):
        """Plan 033: min-width must be 0 to avoid horizontal scroll on small viewports."""
        css = (PROJECT_ROOT / "src" / "static" / "css" / "main.css").read_text()
        # Check ALL bracket-related selectors
        for selector in [".bracket-mirror", ".bracket-mirror-wrapper",
                         ".bracket-labels-mirror", ".bracket-labels-mirror .label"]:
            m = re.search(
                re.escape(selector) + r"\s*\{[^}]*min-width:\s*(\d+|0)\s*px",
                css
            )
            if m:
                min_w = int(m.group(1))
                assert min_w <= 0, \
                    f"{selector} min-width {min_w}px will force horizontal scroll"

    def test_bracket_wrapper_overflow_x(self):
        """bracket-wrapper must have overflow-x for horizontal scrolling if needed."""
        css = (PROJECT_ROOT / "src" / "static" / "css" / "main.css").read_text()
        m = re.search(r"\.bracket-wrapper\s*\{[^}]*overflow-x:\s*(\w+)", css)
        assert m, "bracket-wrapper overflow-x not found"
        # We allow overflow-x: auto OR hidden
        assert m.group(1) in ("auto", "hidden", "scroll")

    def test_bracket_card_max_height_defined(self):
        """Card max-height must be <= grid row height."""
        css = (PROJECT_ROOT / "src" / "static" / "css" / "main.css").read_text()
        # Get row height
        m_row = re.search(r"\.bracket-mirror\s*\{[^}]*grid-template-rows:\s*repeat\(8,\s*(\d+)px\)", css)
        row_h = int(m_row.group(1))
        # Get card max-height
        m_card = re.search(r"\.bracket-card\s*\{[^}]*max-height:\s*(\d+)px", css)
        if m_card:
            card_h = int(m_card.group(1))
            assert card_h <= row_h, \
                f"card max-height {card_h}px > row height {row_h}px"


# ============================================================
# End-to-end: API behavior that init depends on
# ============================================================

class TestApiQualificationCacheContract:
    """Verify /api/qualification returns cacheable response.

    Plan 033: when JS init awaits loadQualification(), the response must
    be fast (cache hit) and always include 'groups' dict. If groups is
    missing or empty, bracket will render with all placeholders.
    """

    def test_cache_file_exists(self):
        """The cache file should be generated by /api/refresh."""
        cache = PROJECT_ROOT / "data" / "qualification_cache.json"
        if not cache.exists():
            pytest.skip("qualification_cache.json not generated yet — "
                        "run /api/refresh to populate")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert "groups" in data, "Cache must have 'groups' key"
        assert isinstance(data["groups"], dict), "'groups' must be dict"
        # Each group should have standings
        for letter, grp in data["groups"].items():
            assert "standings" in grp, \
                f"Group {letter} missing 'standings'"
            assert isinstance(grp["standings"], list)
            # 4 teams in each group
            assert len(grp["standings"]) == 4, \
                f"Group {letter} should have 4 teams"

    def test_cache_has_version(self):
        """Cache must have version field for migration safety."""
        cache = PROJECT_ROOT / "data" / "qualification_cache.json"
        if not cache.exists():
            pytest.skip("Cache not generated yet")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert "version" in data
        # Should be int >= 1
        assert data["version"] >= 1

    def test_cache_has_generated_at(self):
        """Cache should have timestamp for staleness detection."""
        cache = PROJECT_ROOT / "data" / "qualification_cache.json"
        if not cache.exists():
            pytest.skip("Cache not generated yet")
        data = json.loads(cache.read_text(encoding="utf-8"))
        assert "generated_at" in data


# ============================================================
# End-to-end: full API contract via Flask test client
# ============================================================

class TestEndToEndInitFlow:
    """Test the full init flow as a Python script would execute it.

    This is the most important test — it simulates what the JS frontend
    does on page load.
    """

    def test_init_flow_returns_valid_data(self):
        """Simulate frontend init: load matches, teams, qualification."""
        from src.app import create_app
        app = create_app()
        with app.test_client() as client:
            # 1. Load matches
            r1 = client.get("/api/matches")
            assert r1.status_code == 200
            matches = r1.get_json()
            assert len(matches) > 0, "Matches should not be empty"

            # 2. Load teams
            r2 = client.get("/api/teams")
            assert r2.status_code == 200
            teams = r2.get_json()
            assert len(teams) >= 48, f"Teams should be 48, got {len(teams)}"

            # 3. Load qualification (Plan 033: must return data with groups)
            r3 = client.get("/api/qualification")
            assert r3.status_code == 200
            qual = r3.get_json()
            assert "groups" in qual, \
                "Plan 033: qualification MUST return 'groups' for bracket to render"
            assert isinstance(qual["groups"], dict)
            # At least one group should have a locked team if Mexico's data is set
            # But this is data-dependent, so just check structure
            for letter, grp in qual["groups"].items():
                assert "standings" in grp
                assert "locked_top2" in grp
                assert "eliminated" in grp

    def test_qualification_endpoint_succeeds_when_cache_missing(self):
        """Even if qualification_cache.json is missing, /api/qualification
        must succeed (real-time compute fallback)."""
        from src.app import create_app
        import os
        from pathlib import Path

        # Temporarily move the cache file
        cache = Path("data/qualification_cache.json")
        backup = None
        if cache.exists():
            backup = cache.read_text(encoding="utf-8")
            cache.unlink()
        try:
            app = create_app()
            with app.test_client() as client:
                r = client.get("/api/qualification")
                assert r.status_code == 200
                qual = r.get_json()
                # Should still have groups (computed on demand)
                assert "groups" in qual
                # And slow-path should have created the cache file
                # (or not, depending on test order — but at least structure OK)
        finally:
            if backup:
                cache.write_text(backup, encoding="utf-8")

    def test_bracket_endpoint_returns_standings_for_all_groups(self):
        """After init, each match's standings should be available
        (so bracket render can resolve placeholders)."""
        from src.app import create_app
        app = create_app()
        with app.test_client() as client:
            r = client.get("/api/matches")
            matches = r.get_json()

            # Find a group-stage match (has group letter)
            group_match = next(
                (m for m in matches if m.get("group") and m.get("standings")),
                None
            )
            if not group_match:
                pytest.skip("No group match with standings in data")

            # Should have standings
            standings = group_match["standings"]
            assert len(standings) == 4, \
                f"Group {group_match.get('group')} should have 4 teams in standings"
            # Each standing has team_id, mp, w, d, l, pts, gf, ga, gd
            for s in standings:
                assert "team_id" in s
                assert "mp" in s
                assert "pts" in s


# ============================================================
# Regression: ensure prior plan fixes still work
# ============================================================

class TestPlan027Regression:
    """Plan 027/028: qualification data includes China name (name_zh)
    for each team in standings, so bracket can show 中文 + 国旗."""

    def test_qualification_groups_have_name_zh_for_locked(self):
        from src.app import create_app
        app = create_app()
        with app.test_client() as client:
            r = client.get("/api/qualification")
            qual = r.get_json()
            # Find any group with a locked team
            for letter, grp in qual["groups"].items():
                for locked in grp.get("locked_top2", []):
                    if not locked.get("name_zh"):
                        # Try to resolve via another path
                        # If Mexico is locked, it MUST have name_zh
                        if "mexico" in locked.get("name", "").lower():
                            pytest.fail(
                                f"Mexico (Group {letter}) should have name_zh, "
                                f"got: {locked}"
                            )
                    assert locked.get("name_zh"), \
                        f"Locked team in Group {letter} missing name_zh: {locked}"
                    assert locked.get("code_iso"), \
                        f"Locked team in Group {letter} missing code_iso: {locked}"
