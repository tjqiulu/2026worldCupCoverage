"""Match details data layer.

Loads data/details.json (manually maintained) and provides enrichment functions.

Schema:
    {
        "<match_id>": {
            "status": "final" | "live" | "scheduled",
            "score": {"home": int, "away": int},
            "half_time_score": {"home": int, "away": int},  # optional
            "goalscorers": [
                {"team": "home"|"away", "player": str, "minute": int,
                 "type": "goal"|"penalty"|"own_goal"}  # type optional
            ]
        }
    }

If a match is not in details.json, it's treated as "scheduled" (no score).
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DETAILS_FILE = _PROJECT_ROOT / "data" / "details.json"

VALID_STATUSES = {"final", "live", "scheduled"}
VALID_GOAL_TYPES = {"goal", "penalty", "own_goal"}


@lru_cache(maxsize=1)
def _load() -> dict[str, dict[str, Any]]:
    """Load details.json (cached at module level). Empty dict if file missing.

    Skips special keys (starting with `_`) like `_comment` — these are
    documentation/metadata, not match entries.
    """
    if not DETAILS_FILE.exists():
        logging.warning(f"details.json not found at {DETAILS_FILE}")
        return {}
    try:
        raw = json.loads(DETAILS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logging.error(f"details.json is invalid JSON: {e}")
        return {}
    # Strip non-match keys (start with `_`)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def get_details(match_id: str) -> dict[str, Any] | None:
    """Get details for a specific match, or None if not found or malformed."""
    data = _load()
    if match_id not in data:
        return None
    entry = data[match_id]
    if not validate_entry(entry):
        logging.warning(f"Malformed details entry for {match_id}: {entry}")
        return None
    return entry


def enrich_match(m: dict[str, Any]) -> dict[str, Any]:
    """Add 'details' field to a match (None if not in details.json).

    Mutates m in place; returns m.
    """
    details = get_details(m.get("match_id", ""))
    m["details"] = details
    return m


def enrich_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich a list of matches with details (in place)."""
    for m in matches:
        enrich_match(m)
    return matches


# === Plan 012: Merge from worldcup26.ir API ===

def merge_from_api(
    existing: dict[str, dict[str, Any]],
    api_details: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Merge API-fetched details into existing details.

    Rules:
    - Existing entries (manually maintained) take priority — never overwritten by API.
    - New entries from API are added to existing.
    - Returns (merged_dict, num_added) where num_added is the number of
      new entries (not overwriting existing).
    """
    added = 0
    merged = dict(existing)  # copy
    for mid, api_entry in api_details.items():
        if mid not in merged:
            merged[mid] = api_entry
            added += 1
        # else: existing entry wins, skip API
    return merged, added


def load_details() -> dict[str, dict[str, Any]]:
    """Load and parse details.json (always fresh from disk, no cache)."""
    if not DETAILS_FILE.exists():
        return {}
    try:
        raw = json.loads(DETAILS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def save_details(details: dict[str, dict[str, Any]]) -> None:
    """Save details to disk, preserving any _comment key."""
    current: dict[str, Any] = {}
    if DETAILS_FILE.exists():
        try:
            current = json.loads(DETAILS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    # Preserve _comment
    comment = current.get("_comment")
    new_data: dict[str, Any] = dict(details)
    if comment is not None:
        new_data["_comment"] = comment
    DETAILS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DETAILS_FILE.write_text(
        json.dumps(new_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Invalidate the cache so next load picks up the change
    _load.cache_clear()


def validate_entry(entry: Any) -> bool:
    """Validate a single details entry has required structure.

    Returns True if valid, False otherwise (logged).
    """
    if not isinstance(entry, dict):
        return False
    status = entry.get("status")
    if status not in VALID_STATUSES:
        return False
    if status in ("final", "live"):
        # Score required
        score = entry.get("score")
        if not isinstance(score, dict):
            return False
        if not isinstance(score.get("home"), int) or not isinstance(score.get("away"), int):
            return False
        if score["home"] < 0 or score["away"] < 0:
            return False
    # half_time_score optional
    if "half_time_score" in entry:
        hts = entry["half_time_score"]
        if not isinstance(hts, dict):
            return False
        if not isinstance(hts.get("home"), int) or not isinstance(hts.get("away"), int):
            return False
    # goalscorers optional, but if present must be a list of valid dicts
    if "goalscorers" in entry:
        goals = entry["goalscorers"]
        if not isinstance(goals, list):
            return False
        for g in goals:
            if not isinstance(g, dict):
                return False
            if g.get("team") not in ("home", "away"):
                return False
            if not isinstance(g.get("player"), str) or not g["player"]:
                return False
            if not isinstance(g.get("minute"), int) or g["minute"] < 0:
                return False
            if "type" in g and g["type"] not in VALID_GOAL_TYPES:
                return False
    return True


def all_details() -> dict[str, dict[str, Any]]:
    """Return all details (for testing/debugging)."""
    return dict(_load())


def file_exists() -> bool:
    """Whether details.json exists (for tests/audit)."""
    return DETAILS_FILE.exists()


def file_path() -> Path:
    """Path to details.json (for documentation/maintenance)."""
    return DETAILS_FILE
