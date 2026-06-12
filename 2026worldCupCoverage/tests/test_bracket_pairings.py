"""Tests for bracket pairings derivation."""
from pathlib import Path

import pytest

from src.data.bracket_pairings import (
    build_bracket_pairings,
    derive_r32_to_r16,
    parse_w_number,
)


# === Pure helpers ===

class TestParseWNumber:
    @pytest.mark.parametrize("name,expected", [
        ("W73", 73),
        ("W88", 88),
        ("W101", 101),  # for SF winners in Final
        ("W1", 1),
    ])
    def test_valid(self, name, expected):
        assert parse_w_number(name) == expected

    @pytest.mark.parametrize("name", [
        "MEX", "1E", "2A", "3A/B/C/D/F", "L101", "Mexico", "",
    ])
    def test_invalid(self, name):
        assert parse_w_number(name) is None

    def test_none(self):
        assert parse_w_number(None) is None


# === derive_r32_to_r16 ===

class TestDeriveR32ToR16:
    def test_basic(self):
        r16 = {"home": {"name": "W73"}, "away": {"name": "W75"}}
        r32_by_pos = {1: "r32-1", 3: "r32-3"}
        result = derive_r32_to_r16(r16, r32_by_pos)
        assert result == ["r32-1", "r32-3"]

    def test_returns_none_for_missing_position(self):
        r16 = {"home": {"name": "W73"}, "away": {"name": "W999"}}
        r32_by_pos = {1: "r32-1"}  # pos 927 not present
        result = derive_r32_to_r16(r16, r32_by_pos)
        assert result == ["r32-1", None]

    def test_returns_none_for_unparseable(self):
        r16 = {"home": {"name": "1E"}, "away": {"name": "W75"}}
        r32_by_pos = {3: "r32-3"}
        result = derive_r32_to_r16(r16, r32_by_pos)
        assert result == [None, "r32-3"]


# === build_bracket_pairings (integration) ===

REAL_MATCHES = Path("/home/lqiu/.openclaw/workspace/2026worldCupCoverage/data/matches.json")


@pytest.mark.skipif(not REAL_MATCHES.exists(), reason="Real data not present")
class TestBuildBracketPairingsReal:
    @pytest.fixture
    def matches(self):
        import json
        return json.loads(REAL_MATCHES.read_text(encoding="utf-8"))

    @pytest.fixture
    def pairings(self, matches):
        return build_bracket_pairings(matches)

    def test_returns_four_pairing_dicts(self, pairings):
        assert "r16_to_r32" in pairings
        assert "qf_to_r16" in pairings
        assert "sf_to_qf" in pairings
        assert "final_to_sf" in pairings

    def test_r32_positions_has_16(self, pairings):
        assert len(pairings["r32_positions"]) == 16

    def test_r16_to_r32_all_have_2_parents(self, pairings):
        for r16_id, parents in pairings["r16_to_r32"].items():
            assert len(parents) == 2, f"R16 {r16_id} has {len(parents)} parents"
            for p in parents:
                assert p is not None, f"R16 {r16_id} has None parent"

    def test_qf_to_r16_all_have_2_parents(self, pairings):
        for qf_id, parents in pairings["qf_to_r16"].items():
            assert len(parents) == 2

    def test_sf_to_qf_all_have_2_parents(self, pairings):
        for sf_id, parents in pairings["sf_to_qf"].items():
            assert len(parents) == 2

    def test_final_to_sf_has_2_sf(self, pairings):
        for f_id, parents in pairings["final_to_sf"].items():
            assert len(parents) == 2

    def test_specific_pairings_match_fifa_bracket(self, pairings):
        """Verify the known pairings from FIFA WC 2026 bracket."""
        # R16-1: W73 vs W75 → R32 pos 1 and 3
        # Find R16-1 by its first W## reference
        r16_list = list(pairings["r16_to_r32"].items())
        # The first R16 (by chronological order) should be W73 vs W75
        first_r16_id, first_parents = r16_list[0]
        first_parent_codes = [p["home"]["name"] + "/" + p["away"]["name"] for p in first_parents]
        # R32-1 home: 2A, R32-3 home: 1E
        assert first_parent_codes == ["2A/2B", "1E/3A/B/C/D/F"]

    def test_r32_pos_1_is_2A_vs_2B(self, pairings):
        m = pairings["r32_positions"][0]
        assert m["home"]["name"] == "2A"
        assert m["away"]["name"] == "2B"

    def test_r32_pos_16_is_1K_vs_3D_E_I_J_L(self, pairings):
        m = pairings["r32_positions"][15]
        assert m["home"]["name"] == "1K"
        assert m["away"]["name"] == "3D/E/I/J/L"
