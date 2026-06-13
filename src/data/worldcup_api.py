"""World Cup 2026 API client (worldcup26.ir).

Free, open-source REST API specifically for WC 2026.
Provides live scores, match results, and historical data.

No API key required for read access.
Docs: https://worldcup26.ir/api-docs
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import urllib.request

API_BASE = "https://worldcup26.ir/get"
TIMEOUT = 30  # seconds
CACHE_TTL = 300  # 5 minutes

_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_stadiums_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_groups_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_teams_cache: dict[str, Any] = {"data": None, "fetched_at": 0.0}
_endpoint_caches: dict[str, dict[str, Any]] = {
    "stadiums": _stadiums_cache,
    "groups": _groups_cache,
    "teams": _teams_cache,
}


def _fetch_endpoint(cache_key: str, path: str) -> Any:
    """Generic cached GET for an endpoint. Returns parsed JSON or None on error."""
    cache = _endpoint_caches.get(cache_key)
    if cache is None:
        raise ValueError(f"Unknown cache key: {cache_key}")
    now = time.time()
    if cache["data"] is not None and (now - cache["fetched_at"]) < CACHE_TTL:
        return cache["data"]
    url = f"{API_BASE}/{path}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "wc2026-coverage/0.1 (github local app)"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cache["data"] = data
        cache["fetched_at"] = now
        return data
    except Exception as e:
        logging.warning(f"worldcup26.ir {path} fetch failed: {e}")
        return cache["data"]  # stale or None


def fetch_stadiums() -> list[dict[str, Any]]:
    """Fetch all WC 2026 stadiums. Cached 5 min.

    Returns: list of stadium dicts with keys: id, name_en, city_en,
    country_en, capacity, region, fifa_name.
    """
    data = _fetch_endpoint("stadiums", "stadiums")
    if data is None:
        return []
    return data.get("stadiums", [])


def fetch_groups() -> list[dict[str, Any]]:
    """Fetch all WC 2026 groups with current standings. Cached 5 min.

    Returns: list of group dicts with keys: name, teams[].
    Each team: {team_id, mp, w, d, l, pts, gf, ga, gd}.
    """
    data = _fetch_endpoint("groups", "groups")
    if data is None:
        return []
    return data.get("groups", [])


def fetch_teams() -> list[dict[str, Any]]:
    """Fetch all WC 2026 teams. Cached 5 min.

    Returns: list of team dicts with keys: id, name_en, flag, fifa_code, iso2, groups.
    """
    data = _fetch_endpoint("teams", "teams")
    if data is None:
        return []
    return data.get("teams", [])


def get_teams_by_id() -> dict[str, dict[str, Any]]:
    """Return {team_id: team_dict} for all 48 teams, cached.

    Used by the frontend to render standings with team names + flags.
    """
    return {t["id"]: t for t in fetch_teams() if t.get("id")}


def _fetch_raw() -> list[dict[str, Any]]:
    """Fetch all WC 2026 games from worldcup26.ir (with caching)."""
    now = time.time()
    if _cache["data"] is not None and (now - _cache["fetched_at"]) < CACHE_TTL:
        return _cache["data"]

    url = f"{API_BASE}/games"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "wc2026-coverage/0.1 (github local app)"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        games = data.get("games", [])
        _cache["data"] = games
        _cache["fetched_at"] = now
        return games
    except Exception as e:
        logging.warning(f"worldcup26.ir fetch failed: {e}")
        # Return stale cache if available, else empty
        if _cache["data"] is not None:
            return _cache["data"]
        return []


def parse_scorers(scorers_str: str | None) -> list[dict[str, Any]]:
    """Parse API's home_scorers/away_scorers JSON string.

    Input format examples (inconsistent quoting!):
        '{J. Quiñones 9',R. Jiménez 67'}'  (fancy quotes, no comma quotes)
        '{"I.B. Hwang 67'","H.G. Oh 80'"}'  (proper JSON array)
        '{"L. Krejčí 59'"}'  (single-item JSON array)
        'null'

    Output: [{"player": "J. Quiñones", "minute": 9}, ...]
    """
    if not scorers_str or scorers_str in ("null", "NULL"):
        return []

    s = scorers_str.strip()
    if s.startswith("{"):
        s = s[1:]
    if s.endswith("}"):
        s = s[:-1]
    s = s.strip()
    if not s:
        return []

    # Normalize fancy quotes to straight quotes (the API is inconsistent)
    # U+201C "  U+201D "  ->  "
    # U+2018 '  U+2019 '  ->  '
    s_norm = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    # Try as JSON array (preferred — handles player names with special chars)
    try:
        s_arr = f"[{s_norm}]"
        arr = json.loads(s_arr)
        if isinstance(arr, list):
            return _parse_scorer_strings([str(x) for x in arr if x])
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: regex split on goals
    # Each goal looks like "Player Name NN'" or "Player Name NN"
    # Use a regex that finds all "TEXT NUMBER" patterns
    pattern = re.compile(r"([^,]+?)\s+(\d{1,3})\s*'?")
    matches_iter = pattern.finditer(s)
    goals = []
    for m in matches_iter:
        player = m.group(1).strip().strip('"').strip("'")
        minute = int(m.group(2))
        if player:
            goals.append({"player": player, "minute": minute})
    return goals


def _parse_scorer_strings(items: list[str]) -> list[dict[str, Any]]:
    """Parse list of 'Player Name N' strings into structured goals."""
    goals = []
    for item in items:
        # Match: "Player Name" followed by "NN'" or "NN"
        # Player name can have spaces, dots (e.g., "I.B. Hwang"), etc.
        m = re.match(r"^(.+?)\s+(\d{1,3})\s*'?\s*$", item.strip())
        if m:
            goals.append({
                "player": m.group(1).strip(),
                "minute": int(m.group(2)),
            })
        elif item.strip():
            # No minute found, just add the player with minute 0
            goals.append({"player": item.strip(), "minute": 0})
    return goals


def _to_int(value: Any) -> int:
    """Convert API score string to int, handling 'null'/'None'/etc."""
    if value is None or value == "null" or value == "NULL" or value == "":
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def game_to_details_entry(game: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one API game to our details.json entry format.

    Returns None for unfinished games.
    """
    if game.get("finished") != "TRUE":
        return None

    home_scorers = parse_scorers(game.get("home_scorers"))
    away_scorers = parse_scorers(game.get("away_scorers"))

    goals = []
    for g in home_scorers:
        goals.append({**g, "team": "home"})
    for g in away_scorers:
        goals.append({**g, "team": "away"})

    return {
        "status": "final",
        "score": {
            "home": _to_int(game.get("home_score")),
            "away": _to_int(game.get("away_score")),
        },
        "goalscorers": goals,
    }


def find_match_id(game: dict[str, Any], matches: list[dict[str, Any]]) -> str | None:
    """Match an API game to our internal match_id by team names.

    Returns None if no match found.
    """
    api_home = (game.get("home_team_name_en") or "").strip()
    api_away = (game.get("away_team_name_en") or "").strip()
    if not api_home or not api_away:
        return None

    for m in matches:
        our_home = (m.get("home", {}).get("name") or "").strip()
        our_away = (m.get("away", {}).get("name") or "").strip()
        if our_home == api_home and our_away == api_away:
            return m["match_id"]
    return None


def fetch_details_for_matches(matches: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fetch API and return details entries for our match_ids.

    Returns dict mapping match_id -> details entry (only for finished games).
    """
    games = _fetch_raw()
    result = {}
    matched = 0
    unmatched = 0
    for game in games:
        entry = game_to_details_entry(game)
        if entry is None:
            continue  # not finished
        mid = find_match_id(game, matches)
        if mid is None:
            unmatched += 1
            continue
        result[mid] = entry
        matched += 1
    logging.info(f"worldcup26.ir: {matched} matched, {unmatched} unmatched finished games")
    return result


def clear_cache() -> None:
    """Clear all in-memory caches (for testing or forced refresh)."""
    _cache["data"] = None
    _cache["fetched_at"] = 0.0
    for c in _endpoint_caches.values():
        c["data"] = None
        c["fetched_at"] = 0.0


def _normalize_city(city: str) -> str:
    """Normalize a city name for fuzzy matching.

    - Lowercase
    - Strip parenthetical suffixes like " (Foxborough)" → "boston"
    - Collapse whitespace
    """
    if not city:
        return ""
    s = city.strip().lower()
    # Remove "(...)" parenthetical
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    # Collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def find_stadium_by_city(city: str | None) -> dict[str, Any] | None:
    """Find a stadium by host city name (used to enrich ICS venues).

    Args:
        city: ICS venue string like "Mexico City" or "Boston (Foxborough)"

    Returns: stadium dict {id, name_en, city_en, country_en, capacity, ...}
             or None if no match.
    """
    if not city:
        return None
    target = _normalize_city(city)
    if not target:
        return None
    stadiums = fetch_stadiums()
    # First pass: exact normalized match
    for s in stadiums:
        if _normalize_city(s.get("city_en", "")) == target:
            return s
    # Second pass: substring match (e.g., "new york" in "new york/new jersey")
    for s in stadiums:
        c = _normalize_city(s.get("city_en", ""))
        if c and (c in target or target in c):
            return s
    return None


def find_group_standings(group_letter: str | None) -> list[dict[str, Any]] | None:
    """Find current standings for a group letter (A-L).

    Returns: list of team standings sorted by pts desc, gd desc, gf desc, OR
             None if group not found.
    Each entry: {team_id, mp, w, d, l, pts, gf, ga, gd}.
    """
    if not group_letter:
        return None
    target = group_letter.strip().upper()
    if not target:
        return None
    groups = fetch_groups()
    for g in groups:
        if (g.get("name") or "").strip().upper() == target:
            teams = g.get("teams", []) or []
            # Sort by pts desc, gd desc, gf desc
            def _key(t: dict[str, Any]) -> tuple[int, int, int]:
                return (
                    _to_int(t.get("pts")),
                    _to_int(t.get("gd")),
                    _to_int(t.get("gf")),
                )
            return sorted(teams, key=_key, reverse=True)
    return None


def last_fetch_age_seconds() -> float | None:
    """How long ago the cache was last refreshed. None if never."""
    if _cache["fetched_at"] == 0.0:
        return None
    return time.time() - _cache["fetched_at"]
