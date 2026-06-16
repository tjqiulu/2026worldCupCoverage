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
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so this works as `python3 src/app.py`
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from src.data.countries import enrich_matches  # noqa: E402
from src.data.details import (
    enrich_matches as enrich_details_matches,
    merge_from_api,
    save_details,
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


def create_app() -> Flask:
    """Flask app factory."""
    app = Flask(__name__)

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
                standings = find_group_standings(m["group"])
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

            age = last_fetch_age_seconds()
            return jsonify({
                "status": "ok",
                "count": len(matches),
                "scores_updated": scores_updated,
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
                "code_iso": (t.get("iso2") or "").lower() or (meta or {}).get("code_iso"),
                "code_fifa": t.get("fifa_code") or (meta or {}).get("code_fifa"),
                "flag_url": t.get("flag"),
            }
        return jsonify(enriched)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=HOST, port=PORT, debug=DEBUG)
