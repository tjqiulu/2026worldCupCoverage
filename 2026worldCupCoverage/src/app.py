"""Flask application for 2026 World Cup Coverage.

Routes:
    GET  /              - Main page
    GET  /api/matches   - All matches (or filter by ?date=YYYY-MM-DD)
    POST /api/refresh   - Re-fetch ICS and rebuild local cache
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so this works as `python3 src/app.py`
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request  # noqa: E402

from src.data.ics_fetcher import fetch_ics  # noqa: E402
from src.data.ics_parser import parse_ics  # noqa: E402

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
MATCHES_FILE = DATA_DIR / "matches.json"

# Server config
HOST = "127.0.0.1"
PORT = 8766  # 8765 occupied by another service on this host


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
        date = request.args.get("date")
        if date:
            matches = [m for m in matches if m["date_utc"].startswith(date)]
        return jsonify(matches)

    @app.route("/api/refresh", methods=["POST"])
    def api_refresh() -> Any:
        try:
            matches = _refresh_matches()
            return jsonify({"status": "ok", "count": len(matches)})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route("/api/health")
    def api_health() -> Any:
        return jsonify({"status": "ok", "matches_loaded": len(load_matches())})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=HOST, port=PORT, debug=True)
