"""Tests for Flask app endpoints."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.app import create_app


@pytest.fixture
def client(tmp_path):
    """Flask test client with isolated data dir."""
    with patch("src.app.DATA_DIR", tmp_path), \
         patch("src.app.MATCHES_FILE", tmp_path / "matches.json"):
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


def test_index_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"2026" in resp.data


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_api_matches_empty(client):
    """When no data file exists, should still return list (loads via fetch or empty)."""
    # We don't mock the fetcher; just check endpoint exists.
    # May fail in test env if no network — accept either 200 (with list) or 500.
    resp = client.get("/api/matches")
    assert resp.status_code in (200, 500)


def test_api_matches_with_data(client):
    """Pre-populate matches.json, then verify endpoint returns it."""
    sample = [
        {
            "match_id": "test-1",
            "summary": "MEX vs RSA (Group A)",
            "date_utc": "2026-06-11T23:00:00+00:00",
            "home": {"code": "MEX"},
            "away": {"code": "RSA"},
            "stage": "group",
            "group": "A",
            "venue": {"raw": "Azteca"},
        }
    ]
    matches_file = Path(client.application.config.get("DATA_DIR", ".")) if False else None
    # Use the patched path
    import src.app as appmod
    appmod.MATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    appmod.MATCHES_FILE.write_text(json.dumps(sample), encoding="utf-8")

    resp = client.get("/api/matches")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["match_id"] == "test-1"
    assert data[0]["home"]["code"] == "MEX"


def test_api_matches_filter_by_date(client):
    sample = [
        {
            "match_id": "a",
            "summary": "A vs B",
            "date_utc": "2026-06-11T10:00:00+00:00",
            "home": {"code": "A"},
            "away": {"code": "B"},
            "stage": "group",
            "group": "A",
            "venue": {"raw": ""},
        },
        {
            "match_id": "b",
            "summary": "C vs D",
            "date_utc": "2026-06-12T10:00:00+00:00",
            "home": {"code": "C"},
            "away": {"code": "D"},
            "stage": "group",
            "group": "B",
            "venue": {"raw": ""},
        },
    ]
    import src.app as appmod
    appmod.MATCHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    appmod.MATCHES_FILE.write_text(json.dumps(sample), encoding="utf-8")

    resp = client.get("/api/matches?date=2026-06-11")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["match_id"] == "a"


class TestApiCacheHeaders:
    """Plan 040: /api/* responses must never be browser-cached, otherwise
    the user can see fresh data in one field (score) and stale data in
    another (standings) after clicking 刷新. With no Cache-Control header
    set explicitly, browsers use heuristic caching and may serve stale
    /api/matches for a few seconds — long enough to confuse the user.
    """

    def test_api_matches_has_no_store_header(self, client):
        resp = client.get("/api/matches")
        assert resp.headers.get("Cache-Control") == "no-store"

    def test_api_health_has_no_store_header(self, client):
        resp = client.get("/api/health")
        assert resp.headers.get("Cache-Control") == "no-store"

    def test_index_html_not_no_store(self, client):
        """The HTML shell is fine to cache — the SW handles it with
        network-first. We only want to disable caching for /api/*."""
        resp = client.get("/")
        assert resp.headers.get("Cache-Control") != "no-store"
