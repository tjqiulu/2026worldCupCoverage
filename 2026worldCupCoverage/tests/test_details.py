"""Tests for match details data layer (Plan 010)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.data.details import (
    DETAILS_FILE,
    all_details,
    enrich_match,
    enrich_matches,
    file_exists,
    file_path,
    get_details,
    validate_entry,
)


# === R1, R2: details.json exists and loadable ===

class TestDetailsFile:
    def test_file_exists(self):
        assert file_exists(), f"details.json missing at {file_path()}"

    def test_file_loadable(self):
        details = all_details()
        assert isinstance(details, dict)

    def test_initial_data_has_at_least_2_matches(self):
        """R13: initial data has at least 2 finished matches for demo."""
        details = all_details()
        # At least 2 entries (we pre-populated MEX vs RSA and KOR vs CZE)
        assert len(details) >= 2, f"Expected ≥ 2 entries, got {len(details)}"

    def test_initial_matches_have_final_status(self):
        details = all_details()
        final_count = sum(1 for e in details.values() if e.get("status") == "final")
        assert final_count >= 2, f"Expected ≥ 2 'final' entries, got {final_count}"


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
            # Clear cache
            from src.data import details
            details._load.cache_clear()
            assert get_details("good_match") is not None
            assert get_details("bad_match") is None
            details._load.cache_clear()


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
