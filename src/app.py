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
from src.data.worldcup_api import fetch_details_for_matches, last_fetch_age_seconds  # noqa: E402

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MATCHES_FILE = DATA_DIR / "matches.json"

# Server config
HOST = "127.0.0.1"
PORT = 8766

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
        date = request.args.get("date")
        if date:
            matches = [m for m in matches if m["date_utc"].startswith(date)]
        return jsonify(matches)

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh() -> Any:
        try:
            matches = _refresh_matches()
            # Plan 012: also pull live scores from worldcup26.ir
            scores_updated = 0
            try:
                api_details = fetch_details_for_matches(matches)
                if api_details:
                    from src.data.details import load_details
                    existing = load_details()
                    merged, scores_updated = merge_from_api(existing, api_details)
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

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=HOST, port=PORT, debug=DEBUG)
