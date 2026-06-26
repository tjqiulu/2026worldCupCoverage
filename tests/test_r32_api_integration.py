"""Tests for Plan 044 — /api/matches R32 resolution integration.

Verifies that the FIFA bracket matrix is applied to the API response
so the frontend can render resolved 3rd-place opponents for R32
1X-vs-3Y matches.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.app import _build_r32_resolution, _resolve_r32_match, create_app


# === Real-data integration test ===

def test_r32_resolution_usa_gets_bosnia_in_live_data():
    """Smoke test against the live data files (no Flask needed)."""
    project_root = Path(__file__).resolve().parents[1]
    matches = json.loads((project_root / "data" / "matches.json").read_text(encoding="utf-8"))
    res = _build_r32_resolution(matches)
    assert "D" in res, f"1D (USA) not in resolution keys: {list(res.keys())}"
    assert res["D"] is not None
    assert res["D"]["team_id"] == "6", f"USA should play Bosnia, got {res['D']}"
    assert res["D"]["state"] == "locked"


def test_r32_resolution_all_eight_1st_place_assigned():
    project_root = Path(__file__).resolve().parents[1]
    matches = json.loads((project_root / "data" / "matches.json").read_text(encoding="utf-8"))
    res = _build_r32_resolution(matches)
    # All 8 1st-place groups in FIFA matrix
    expected_keys = {"A", "B", "D", "E", "G", "I", "K", "L"}
    assert set(res.keys()) == expected_keys
    # At least 3 should be locked (B, E, F all at 4pts final)
    locked = [k for k, v in res.items() if v and v.get("state") == "locked"]
    assert len(locked) >= 3, f"Expected at least 3 locked, got {locked}"


def test_resolve_r32_match_with_real_team_1x_side():
    """The USA case: home is real (USA), away is 3B/E/F/I/J placeholder."""
    project_root = Path(__file__).resolve().parents[1]
    matches = json.loads((project_root / "data" / "matches.json").read_text(encoding="utf-8"))
    usa_match = next(
        m for m in matches
        if m.get("stage") == "r32" and "USA" in m.get("home", {}).get("name", "")
    )
    res = _build_r32_resolution(matches)
    # Build team_name_to_group for the test
    from src.data.worldcup_api import get_teams_by_id
    from src.data.countries import all_countries
    from src.data.details import build_team_id_map
    teams = get_teams_by_id()
    name_to_id = build_team_id_map(teams, countries=all_countries())
    tid_to_group = {
        str(tid): t.get("groups", "")
        for tid, t in teams.items()
        if t.get("groups")
    }
    name_to_group = {
        name: tid_to_group[str(tid)]
        for name, tid in name_to_id.items()
        if str(tid) in tid_to_group
    }
    result = _resolve_r32_match(usa_match, res, name_to_group)
    assert result is not None
    assert result["team_id"] == "6"
    assert result["name_zh"] == "波黑"


def test_resolve_r32_match_with_both_placeholders():
    """1D vs 3B/E/F/I/J case, where 1D is also a placeholder (this is
    hypothetical — the real data has USA as the 1D team, not a placeholder)."""
    m = {
        "home": {"name": "1D"},
        "away": {"name": "3B/E/F/I/J"},
    }
    res = {"D": {"team_id": "6", "name": "Bosnia and Herzegovina",
                  "name_zh": "波黑", "code_iso": "ba", "state": "locked"}}
    result = _resolve_r32_match(m, res, None)
    assert result is not None
    assert result["team_id"] == "6"


def test_resolve_r32_match_2x_vs_2y_returns_none():
    """R32 1st-vs-2nd match should not get a resolution (no 3rd place involved)."""
    m = {"home": {"name": "2A"}, "away": {"name": "2B"}}
    res = {}  # would be empty since no 3rd place needed
    result = _resolve_r32_match(m, res, None)
    assert result is None


# === API endpoint integration ===

@pytest.fixture
def client(tmp_path):
    """Flask test client using live data/ directory."""
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    with patch("src.app.DATA_DIR", data_dir), \
         patch("src.app.MATCHES_FILE", data_dir / "matches.json"), \
         patch("src.app.QUALIFICATION_CACHE_FILE", data_dir / "qualification_cache.json"):
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


def test_api_matches_contains_r32_resolved_opponent(client):
    """The /api/matches endpoint should attach r32_resolved_opponent to R32 matches."""
    resp = client.get("/api/matches")
    assert resp.status_code == 200
    data = resp.get_json()
    r32_matches = [m for m in data if m.get("stage") == "r32"]
    assert len(r32_matches) == 16  # All 16 R32 matches
    # At least 7 of 8 1st-vs-3rd matches should have a resolution
    resolved = [m for m in r32_matches if "r32_resolved_opponent" in m]
    assert len(resolved) >= 7, f"Expected ≥7 resolved R32 matches, got {len(resolved)}"
    # USA's R32 match should resolve to Bosnia
    usa_match = next(
        m for m in r32_matches
        if "USA" in m.get("home", {}).get("name", "")
    )
    assert "r32_resolved_opponent" in usa_match
    ro = usa_match["r32_resolved_opponent"]
    assert ro["team_id"] == "6"
    assert ro["name_zh"] == "波黑"
    assert ro["state"] == "locked"
