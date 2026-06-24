"""Flask application for 2026 World Cup Coverage.

Routes:
    GET  /              - Main page
    GET  /api/matches   - All matches (or filter by ?date=YYYY-MM-DD)
    POST /api/refresh   - Re-fetch ICS and rebuild local cache
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so this works as `python3 src/app.py`
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from src.data.countries import all_countries, enrich_matches  # noqa: E402
from src.data.details import (
    build_team_id_map,
    compute_standings_from_details,
    enrich_matches as enrich_details_matches,
    load_details,
    merge_from_api,
    save_details,
)
from src.data.qualification import (  # noqa: E402
    compute_best_3rd_race,
    compute_full_qualification,
    compute_per_group,
)
from src.data.ics_fetcher import fetch_ics  # noqa: E402
from src.data.ics_parser import parse_ics  # noqa: E402
from src.data.worldcup_api import (  # noqa: E402
    clear_cache as clear_api_cache,
    fetch_details_for_matches,
    find_group_standings,
    find_stadium_by_city,
    get_teams_by_id,
    last_fetch_age_seconds,
)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MATCHES_FILE = DATA_DIR / "matches.json"

# Server config
# LAN-accessible: 0.0.0.0 binds to all interfaces (phone on same WiFi
# can reach via http://192.168.1.44:8766). Loopback-only was 127.0.0.1.
# Plan 021: PORT reads $PORT env var (Render injects 10000) with
# local default 8766 — backward compatible with `python src/app.py`.
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 8766))

# Debug mode: off by default for end-user launches (set FLASK_DEBUG=1 to enable)
# When debug=True, Flask uses a reloader that spawns a child process on startup,
# which can cause the first browser request to fail with "Failed to fetch"
# if it hits during the reloader handoff window.
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"  # 8765 occupied by another service on this host


def load_matches() -> list[dict[str, Any]]:
    """Load matches from local cache, or fetch+parse on first run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MATCHES_FILE.exists():
        return _refresh_matches()
    return json.loads(MATCHES_FILE.read_text(encoding="utf-8"))


def _refresh_matches() -> list[dict[str, Any]]:
    """Fetch ICS, parse, save to matches.json, return matches."""
    ics_path = fetch_ics(force=True)
    matches = parse_ics(ics_path)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MATCHES_FILE.write_text(
        json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return matches


def _local_or_api_standings(
    group_letter: str,
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Plan 025: Compute standings locally from details.json; fall back
    to worldcup26.ir API only if we have no final matches in this group.

    The local data is always in sync with the goalscorers we display, so
    showing locally-derived standings guarantees the modal is internally
    consistent. The API's `/get/groups` is sometimes stale (we saw Iraq-
    Norway still at 0 PTS hours after the match finished on 2026-06-17).
    """
    try:
        all_details = load_details()
        # Build {team_name_en: team_id} map from the teams endpoint.
        # The teams list is cached for 5 min in worldcup_api.
        teams = get_teams_by_id()
        # Plan 027: multi-key alias resolver. Without this, baires ICS
        # team names like "Bosnia & Herzegovina" / "USA" / "DR Congo"
        # fail to match worldcup26.ir's "Bosnia and Herzegovina" /
        # "United States" / "Democratic Republic of the Congo", and
        # compute_standings_from_details silently drops entire matches.
        # countries.json (keyed by ICS-style names) bridges abbreviations
        # like "DR" → "Democratic Republic" that _norm_team_key can't
        # derive from the API name alone.
        name_to_id = build_team_id_map(teams, countries=all_countries())
        local = compute_standings_from_details(
            group_letter, all_details, matches, name_to_id
        )
        if local is not None:
            return local
    except Exception as e:
        # Don't break the request on local failure — fall back to API.
        print(f"Warning: local standings computation failed: {e}")

    # Fallback: worldcup26.ir API
    return find_group_standings(group_letter)


def create_app() -> Flask:
    """Flask app factory."""
    app = Flask(__name__)

    # Plan 040: never let the browser cache /api/* responses. Without an
    # explicit Cache-Control, browsers use heuristic caching and may serve
    # a stale /api/matches after a 刷新 click (user reported 2026-06-24:
    # modal showed fresh score but stale 3-team standings). The 60s
    # widget auto-poll and the modal re-render are no help if the network
    # response itself is stale. /api/* is dynamic — always revalidate.
    @app.after_request
    def _no_cache_api(response):
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/")
    def index() -> str:
        return render_template("index.html")

    @app.route("/api/matches")
    def api_matches() -> Any:
        matches = load_matches()
        enrich_matches(matches)
        enrich_details_matches(matches)
        # Plan 015: enrich with stadium (by city) and group standings
        for m in matches:
            venue = m.get("venue") or {}
            city = venue.get("raw") or venue.get("name")
            if city:
                stadium = find_stadium_by_city(city)
                if stadium:
                    venue["stadium"] = {
                        "name": stadium.get("fifa_name") or stadium.get("name_en"),
                        "city": stadium.get("city_en"),
                        "country": stadium.get("country_en"),
                        "capacity": stadium.get("capacity"),
                    }
                    m["venue"] = venue
            # Group standings: only for group stage with a valid group letter
            if m.get("stage") == "group" and m.get("group"):
                # Plan 025: local-first — worldcup26.ir `/get/groups` is
                # sometimes stale (Iraq-Norway 2026-06-17 had API showing
                # 0 PTS hours after the match finished). We compute from
                # our own details.json as the source of truth.
                standings = _local_or_api_standings(m["group"], matches)
                if standings is not None:
                    m["standings"] = standings
        date = request.args.get("date")
        if date:
            matches = [m for m in matches if m["date_utc"].startswith(date)]
        return jsonify(matches)

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh() -> Any:
        try:
            matches = _refresh_matches()
            # Plan 016: bypass the 5-min in-memory cache so a manual refresh
            # always hits the worldcup26.ir API (the previous behaviour could
            # hide a freshly-published score for up to 5 minutes).
            clear_api_cache()
            # Plan 012: also pull live scores from worldcup26.ir
            scores_updated = 0
            try:
                api_details = fetch_details_for_matches(matches)
                if api_details:
                    from src.data.details import load_details
                    existing = load_details()
                    merged, scores_updated, _ = merge_from_api(existing, api_details)
                    if scores_updated > 0:
                        save_details(merged)
            except Exception as api_err:
                # API failure is non-fatal — keep existing details
                print(f"Warning: worldcup26.ir API failed: {api_err}")

            # Plan 031: refresh qualification cache after matches update
            qualification_refreshed = False
            try:
                _compute_and_cache_qualification()
                qualification_refreshed = True
            except Exception as qual_err:
                print(f"Warning: qualification cache refresh failed: {qual_err}")

            age = last_fetch_age_seconds()
            return jsonify({
                "status": "ok",
                "count": len(matches),
                "scores_updated": scores_updated,
                "qualification_refreshed": qualification_refreshed,
                "last_refresh_seconds_ago": round(age) if age is not None else None,
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/health")
    def api_health() -> Any:
        matches = load_matches()
        enrich_matches(matches)
        enrich_details_matches(matches)
        return jsonify({"status": "ok", "matches_loaded": len(matches)})

    @app.route("/api/teams")
    def api_teams() -> Any:
        """Plan 015: Team metadata (id -> {name, name_zh, code_iso, flag_url, ...}).
        Used by the frontend to render standings with team names + flags.
        Merges worldcup26.ir /get/teams with our countries.json for bilingual names.
        """
        from src.data.countries import lookup as lookup_country
        teams = get_teams_by_id()
        enriched = {}
        for tid, t in teams.items():
            meta = lookup_country(t.get("name_en") or "")
            enriched[tid] = {
                "name": t.get("name_en") or tid,
                "name_zh": (meta or {}).get("name_zh"),
                "code_iso": _resolve_code_iso(t.get("iso2"), meta),
                "code_fifa": t.get("fifa_code") or (meta or {}).get("code_fifa"),
                "flag_url": t.get("flag"),
            }
        return jsonify(enriched)

    # Plan 031: register qualification route via add_url_rule (handler is module-level)
    app.add_url_rule("/api/qualification", "api_qualification", _api_qualification_handler)

    return app

# Module-level helper functions for /api/qualification.
# Defined at module level (not inside create_app) so /api/refresh can

# === Plan 031: Module-level qualification helpers ===

QUALIFICATION_CACHE_FILE = DATA_DIR / "qualification_cache.json"
QUALIFICATION_CACHE_VERSION = 1


def _resolve_code_iso(api_iso2: str | None, meta: dict | None) -> str:
    """Resolve the code_iso flag-icons CSS suffix for a team.

    worldcup26.ir's `iso2` field is sometimes wrong — for England/Scotland
    it returns the 3-letter FIFA code ('ENG' / 'SCO') instead of a 2-letter
    ISO 3166-1 code. flag-icons expects 2-letter codes (`fi-gb` etc.), so
    we only trust the API value when it's a valid 2-letter alpha code.
    Otherwise we fall back to our curated countries.json entry.
    """
    api = (api_iso2 or "").strip().lower()
    if len(api) == 2 and api.isalpha():
        return api
    return (meta or {}).get("code_iso", "") or ""


def _compute_and_cache_qualification() -> dict[str, Any]:
    """Compute qualification state and persist to JSON cache.

    Plan 031: writes data/qualification_cache.json so the frontend can
    fetch instantly without waiting for real-time computation on every
    page load. The /api/qualification route reads this cache first.
    """
    from src.data.countries import lookup as lookup_country
    matches = load_matches()
    enrich_matches(matches)
    enrich_details_matches(matches)
    all_details = load_details()
    teams = get_teams_by_id()
    name_to_id = build_team_id_map(teams, countries=all_countries())

    group_standings: dict[str, list] = {}
    team_name_cache: dict[str, dict] = {}
    for letter in "ABCDEFGHIJKL":
        standings = compute_standings_from_details(
            letter, all_details, matches, name_to_id
        )
        if standings:
            group_standings[letter] = standings
            for t in standings:
                if t["team_id"] not in team_name_cache:
                    api_team = teams.get(t["team_id"], {})
                    meta = lookup_country(api_team.get("name_en", ""))
                    team_name_cache[t["team_id"]] = {
                        "name": api_team.get("name_en", t["team_id"]),
                        "name_zh": (meta or {}).get("name_zh", ""),
                        "code_iso": _resolve_code_iso(api_team.get("iso2"), meta),
                    }

    result = compute_full_qualification(group_standings)

    def _team_info(tid: str) -> dict:
        d = team_name_cache.get(tid, {})
        return {
            "team_id": tid,
            "name": d.get("name", tid),
            "name_zh": d.get("name_zh", ""),
            "code_iso": d.get("code_iso", ""),
        }

    for g in result["groups"].values():
        for lst_key in ("locked_top2", "favored_top2", "eliminated"):
            g[lst_key] = [
                {**_team_info(t["team_id"]), "reason": t.get("reason", "")}
                for t in g[lst_key]
            ]
        g["pending"] = [
            {**_team_info(t["team_id"]), "max_pts": t.get("max_pts"), "min_pts": t.get("min_pts")}
            for t in g["pending"]
        ]
        if g.get("third_place"):
            tid = g["third_place"]["team_id"]
            g["third_place"] = {**_team_info(tid), **(g["third_place"] or {})}

    best_3rd = result["best_3rd_race"]
    best_3rd["rankings"] = [
        {**_team_info(r["team_id"]), **r}
        for r in best_3rd["rankings"]
    ]
    for lst_key in ("locked_top8", "locked_bot4"):
        best_3rd[lst_key] = [
            {**_team_info(t["team_id"]), "reason": t.get("reason", "")}
            for t in best_3rd[lst_key]
        ]
    best_3rd["pending"] = [
        _team_info(tid) for tid in best_3rd["pending"]
    ]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache_payload = {
        **result,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": QUALIFICATION_CACHE_VERSION,
    }
    QUALIFICATION_CACHE_FILE.write_text(
        json.dumps(cache_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return result


def _api_qualification_handler() -> Any:
    """Plan 029 + Plan 031: per-group qualification + best 3rd race.

    Reads from data/qualification_cache.json when available (fast path),
    otherwise computes on demand and caches.
    """
    # Fast path — read JSON cache
    if QUALIFICATION_CACHE_FILE.exists():
        try:
            cache = json.loads(QUALIFICATION_CACHE_FILE.read_text(encoding="utf-8"))
            if cache.get("version") == QUALIFICATION_CACHE_VERSION:
                return jsonify({
                    "groups": cache.get("groups", {}),
                    "best_3rd_race": cache.get("best_3rd_race", {}),
                    "cached": True,
                    "generated_at": cache.get("generated_at"),
                })
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: qualification cache read failed: {e}")

    # Slow path: compute + write cache
    result = _compute_and_cache_qualification()
    return jsonify({
        **result,
        "cached": False,
    })


if __name__ == "__main__":
    app = create_app()
    app.run(host=HOST, port=PORT, debug=DEBUG)
