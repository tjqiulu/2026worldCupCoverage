"""ICS file fetcher with local cache.

Pulls the baires/fifa-cal-2026 calendar ICS file and caches it locally.
Cache TTL: 1 hour (per user preference "刷新即可").
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import requests

# Default ICS URL — baires calendar, English version (most complete for now)
DEFAULT_ICS_URL = (
    "https://cdn.jsdelivr.net/gh/baires/fifa-cal-2026@master/calendars/en.ics"
)

# Cache location: <project>/data/.cache/wc2026.ics
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = _PROJECT_ROOT / "data" / ".cache"
CACHE_FILE = CACHE_DIR / "wc2026.ics"
CACHE_TTL = timedelta(hours=1)

REQUEST_TIMEOUT = 30  # seconds


def fetch_ics(url: str = DEFAULT_ICS_URL, force: bool = False) -> Path:
    """Fetch ICS file, with local cache.

    Args:
        url: ICS URL to fetch.
        force: If True, ignore cache and re-fetch.

    Returns:
        Path to the (cached) ICS file.

    Raises:
        requests.RequestException: If fetch fails and no cache exists.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not force and _is_cache_fresh():
        return CACHE_FILE

    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    CACHE_FILE.write_bytes(resp.content)
    # Touch mtime so cache TTL is from now
    CACHE_FILE.touch()
    return CACHE_FILE


def _is_cache_fresh() -> bool:
    """Check if local cache exists and is within TTL."""
    if not CACHE_FILE.exists():
        return False
    mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
    return datetime.now() - mtime < CACHE_TTL


def cache_age() -> timedelta | None:
    """Return age of local cache, or None if no cache."""
    if not CACHE_FILE.exists():
        return None
    mtime = datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
    return datetime.now() - mtime
