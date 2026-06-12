"""Country metadata: name_en -> {name_zh, code_iso, code_fifa}.

Used to enrich match data with flag icons and bilingual team names.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
COUNTRIES_FILE = _PROJECT_ROOT / "data" / "countries.json"


@lru_cache(maxsize=1)
def _load() -> dict[str, dict[str, str]]:
    """Load countries.json (cached at module level)."""
    return json.loads(COUNTRIES_FILE.read_text(encoding="utf-8"))


def lookup(name_en: str | None) -> dict[str, str] | None:
    """Look up country info by English name (as in baires ICS).

    Returns None if not found.
    """
    if not name_en:
        return None
    return _load().get(name_en)


def enrich_match(m: dict[str, Any]) -> dict[str, Any]:
    """Add name_zh/code_iso/code_fifa to home/away based on team name.

    Idempotent and safe — leaves placeholder codes (1E, 2A, W86, L101) alone.
    Mutates m in place for efficiency, but returns m for chaining.
    """
    for side in ("home", "away"):
        info = m.get(side)
        if not info:
            continue
        name = info.get("name")
        meta = lookup(name)
        if meta:
            info["name_zh"] = meta["name_zh"]
            info["code_iso"] = meta["code_iso"]
            info["code_fifa"] = meta["code_fifa"]
    return m


def enrich_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enrich a list of matches (in place)."""
    for m in matches:
        enrich_match(m)
    return matches


def all_countries() -> dict[str, dict[str, str]]:
    """Return all countries (for testing/debugging)."""
    return dict(_load())


def is_placeholder(name: str | None) -> bool:
    """True if name is a FIFA bracket placeholder (1E, 2A, W86, L101, etc.).

    These are not real teams — they're references to positions in the bracket
    (1st/2nd/3rd place in a group, or winner/loser of a prior match).
    """
    if not name:
        return False
    return bool(name) and (
        name.startswith(("W", "L", "1", "2", "3")) and any(c.isdigit() for c in name)
    )
