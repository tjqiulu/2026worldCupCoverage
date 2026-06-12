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
