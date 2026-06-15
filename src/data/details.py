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
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DETAILS_FILE = _PROJECT_ROOT / "data" / "details.json"

VALID_STATUSES = {"final", "live", "scheduled"}
VALID_GOAL_TYPES = {"goal", "penalty", "own_goal"}


def _load() -> dict[str, dict[str, Any]]:
    """Load details.json (fresh from disk on every call).

    Plan 016 fix: previously this was @lru_cache(maxsize=1) which meant
    manual edits to details.json (e.g., correcting a wrong goal time) were
    not seen until the server was restarted. We tried invalidating the
    cache in save_details() but that didn't help for manual edits.

    The file is small (~5KB) and the request rate is low, so the lru_cache
    optimization wasn't worth the correctness risk. Removed in commit
    that fixed the user's "Larin 78' vs 11'" complaint.
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

def _is_incomplete(entry: dict[str, Any]) -> bool:
    """Return True if a manually-maintained entry looks incomplete.

    Heuristic (Plan 017 + 017.1):
    - A 'final' entry with a score is incomplete if its goalscorers list
      is shorter than the total goals implied by the score.
    - A 'final' entry is also incomplete if ANY goal has minute=0 — real
      match goals are minute 1+, so minute=0 is a strong signal of
      malformed hand-maintained data (e.g. minute info accidentally
      stuffed into the player name string like "K. Havertz 45'+5'(p)").

    Returns False when we can't tell (e.g., no score, no goalscorers key).
    """
    score = entry.get("score") or {}
    goals = entry.get("goalscorers") or []
    if not isinstance(score, dict):
        return False
    if "home" not in score or "away" not in score:
        return False
    home = score.get("home")
    away = score.get("away")
    if not isinstance(home, int) or not isinstance(away, int):
        return False
    if home < 0 or away < 0:
        return False
    if len(goals) < (home + away):
        return True
    # Plan 017.1: any goal with minute=0 is treated as malformed
    if any(
        isinstance(g, dict) and g.get("minute") == 0
        for g in goals
    ):
        return True
    return False


def merge_from_api(
    existing: dict[str, dict[str, Any]],
    api_details: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], int, int]:
    """Merge API-fetched details into existing details.

    Rules (Plan 017):
    - Existing entries with a COMPLETE goalscorers list win over API
      (protects manual corrections like the Larin 78' fix in 965e9ac9ce78).
    - Existing entries that look INCOMPLETE (goalscorers count < score sum)
      are OVERWRITTEN by the API entry — the API is treated as the
      authoritative source for finished games we have a hand-maintained stub for.
    - New entries from the API are added.
    - Returns (merged_dict, num_changed, num_overwritten) where:
        - num_changed = num_added + num_overwritten
        - num_overwritten = entries where the API replaced an incomplete stub
    """
    added = 0
    overwritten = 0
    merged = dict(existing)  # copy
    for mid, api_entry in api_details.items():
        if mid not in merged:
            merged[mid] = api_entry
            added += 1
            continue
        existing_entry = merged[mid]
        if _is_incomplete(existing_entry):
            logging.warning(
                f"merge_from_api: {mid} existing entry is incomplete "
                f"(goalscorers < score sum), overriding with API data"
            )
            merged[mid] = api_entry
            overwritten += 1
        # else: existing entry is complete, keep it (manual corrections win)
    return merged, added + overwritten, overwritten


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
    """Save details to disk, preserving any _comment key.

    Also invalidates the _load() lru_cache so subsequent reads see the new data.
    Plan 016 fix: previously the lru_cache held stale data until server restart.
    """
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
    # Plan 016: lru_cache was removed from _load(); no cache invalidation needed.


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
            if g.get("type") is not None and g["type"] not in VALID_GOAL_TYPES:
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
