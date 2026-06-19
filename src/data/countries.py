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


# Plan 028: explicit alias table for known cross-source variants that
# neither exact match nor normalize can derive. Keyed by the API's
# spelling (what worldcup26.ir returns) → the ICS key in countries.json.
#
# When to add an entry:
#   - The two data sources use different strings for the same country
#   - normalize() cannot derive one from the other (i.e. it's an
#     abbreviation, not just punctuation/whitespace)
#
# Currently covers 2 of the 3 known cases. Bosnia is covered by
# normalize() (Pass 2), so it's not in this table.
_TEAM_NAME_ALIASES: dict[str, str] = {
    "United States": "USA",
    "Democratic Republic of the Congo": "DR Congo",
}


def norm_team_key(s: str | None) -> str:
    """Normalize a team name for fuzzy lookup.

    Plan 027/028 shared helper. Covers minor variations between
    data sources:
      - " & " → " and " (Bosnia & Herzegovina ↔ Bosnia and Herzegovina)
      - lowercase
      - collapse whitespace
      - strip ASCII punctuation (keeps alnum + space, so Unicode
        letters like "Curaçao" / "Côte d'Ivoire" stay intact)

    Returns "" for empty/None input.
    """
    if not s:
        return ""
    s = s.replace("&", "and")
    s = "".join(c for c in s if c.isalnum() or c.isspace())
    s = " ".join(s.split()).lower()
    return s


def lookup(name_en: str | None) -> dict[str, str] | None:
    """Look up country info by English name (3-pass fallback, Plan 028).

    countries.json is keyed by baires ICS names (e.g. "Bosnia &
    Herzegovina", "USA", "DR Congo") but worldcup26.ir API uses
    different spellings ("Bosnia and Herzegovina", "United States",
    "Democratic Republic of the Congo"). Exact match fails across
    data sources, so we fall back to:

      1. Exact match (preserved for performance and predictability)
      2. Normalized match (lowercase, & → and, collapse whitespace)
      3. code_fifa / code_iso reverse lookup (catches "United States"
         via code_fifa="USA", "Democratic Republic of the Congo" via
         code_fifa="COD")

    Returns None if all 3 passes fail.
    """
    if not name_en:
        return None
    data = _load()
    # Pass 1: exact
    if name_en in data:
        return data[name_en]
    # Pass 2: normalized
    nk = norm_team_key(name_en)
    if nk:
        for k, v in data.items():
            if norm_team_key(k) == nk:
                return v
    # Pass 3: explicit alias table for known cross-source variants
    # (e.g. API "United States" → countries.json key "USA")
    alias = _TEAM_NAME_ALIASES.get(name_en)
    if alias and alias in data:
        return data[alias]
    # Pass 4: code_fifa / code_iso reverse lookup. This catches cases
    # where the input happens to BE the code (e.g. caller passes "USA"
    # or "US" directly). The interesting cross-source cases (Pass 3)
    # are handled above.
    nk_upper = name_en.strip().upper()
    for v in data.values():
        if (v.get("code_fifa") or "").upper() == nk_upper:
            return v
        if (v.get("code_iso") or "").upper() == nk_upper:
            return v
    return None


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
