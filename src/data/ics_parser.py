"""ICS file parser.

Parses baires/fifa-cal-2026 ICS file into structured match dicts.

Real ICS format (from baires repo):
    SUMMARY:Mexico vs South Africa
    DESCRIPTION:Matchday 1\nGroup: Group A\nVenue: Mexico City
    LOCATION:Mexico City

Plan 002 scope:
    - Parse SUMMARY into home/away country names
    - Parse DESCRIPTION for matchday + group
    - Leave country code/flag/name_zh to Plan 003 (country mapping table)
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, date
from pathlib import Path
from typing import Any

from icalendar import Calendar


def parse_ics(path: Path) -> list[dict[str, Any]]:
    """Parse ICS file into list of match dicts, sorted by date.

    Returns:
        List of match dicts. Each dict has:
        - match_id: str
        - summary: str (original ICS SUMMARY)
        - date_utc: str (ISO 8601 with timezone)
        - home: {"name": str}
        - away: {"name": str}
        - stage: str (group | r32 | r16 | qf | sf | third | final | unknown)
        - group: str | None (A–L for group stage)
        - matchday: int | None (1–3 for group stage)
        - venue: {"name": str, "raw": str}
    """
    cal = Calendar.from_ical(path.read_bytes())
    matches: list[dict[str, Any]] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        match = _parse_vevent(component)
        if match is not None:
            matches.append(match)
    matches.sort(key=lambda m: m["date_utc"])
    return matches


def _parse_vevent(component: Any) -> dict[str, Any] | None:
    """Parse a single VEVENT into a match dict."""
    summary = str(component.get("SUMMARY", ""))
    dtstart_prop = component.get("DTSTART")
    if dtstart_prop is None:
        return None
    dtstart = dtstart_prop.dt
    location = str(component.get("LOCATION", ""))
    description = str(component.get("DESCRIPTION", ""))
    uid = str(component.get("UID", ""))

    # Normalize date to ISO string (preserve timezone if present)
    if isinstance(dtstart, datetime):
        date_utc = dtstart.isoformat()
    elif isinstance(dtstart, date):
        date_utc = datetime(dtstart.year, dtstart.month, dtstart.day).isoformat() + "+00:00"
    else:
        return None

    teams = _parse_summary(summary)
    if len(teams) < 2:
        # Not a match (e.g., calendar event, TBD before teams known)
        return None

    # Parse description for matchday + group OR knockout stage
    matchday = _parse_matchday(description)
    group = _parse_group(description)
    knockout_stage = _parse_knockout_stage(description)

    if group:
        stage = "group"
    elif knockout_stage:
        stage = knockout_stage
    else:
        stage = "unknown"

    return {
        "match_id": uid.strip() or _make_id(summary, date_utc),
        "summary": summary.strip(),
        "date_utc": date_utc,
        "home": {"name": teams[0]},
        "away": {"name": teams[1]},
        "stage": stage,
        "group": group,
        "matchday": matchday,
        "venue": {"name": location.strip(), "raw": location.strip()},
    }


def _parse_summary(summary: str) -> list[str]:
    """Extract team names from 'Country A vs Country B' pattern.

    baires/fifa-cal-2026 updates SUMMARY in place as matches finish:
        "Mexico vs South Africa"          (pre-match)
        "Mexico 2-0 South Africa"         (post-match, with score)
    Both formats must be accepted, otherwise already-played matches get
    dropped from the calendar entirely.

    Returns empty list if pattern not found. Names are kept as-is (preserves
    case, e.g., "South Korea", "Czech Republic").
    """
    # Normalize the post-match "X 2-0 Y" form back to "X vs Y" so a single
    # downstream regex handles both shapes.
    normalized = re.sub(r"\s+\d+\s*-\s*\d+\s+", " vs ", summary)
    # Match "X vs Y" — accept multi-word country names
    m = re.match(r"^(.+?)\s+vs\.?\s+(.+?)$", normalized, re.IGNORECASE)
    if m:
        return [m.group(1).strip(), m.group(2).strip()]
    return []


def _parse_matchday(description: str) -> int | None:
    """Extract matchday number from DESCRIPTION ('Matchday 1').

    Returns None if not found.
    """
    m = re.search(r"Matchday\s+(\d+)", description, re.IGNORECASE)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _parse_group(description: str) -> str | None:
    """Extract group letter from DESCRIPTION ('Group: Group A').

    Returns letter ('A' through 'L') or None if not found.
    """
    m = re.search(r"Group:\s*Group\s+([A-Z])", description, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def _parse_knockout_stage(description: str) -> str | None:
    """Extract knockout stage from DESCRIPTION.

    Handles:
        'Round of 32'        -> 'r32'
        'Round of 16'        -> 'r16'
        'Quarter-finals'     -> 'qf'
        'Semi-finals'        -> 'sf'
        'Third Place Match'  -> 'third'
        'Final'              -> 'final'
    """
    text = description.lower().strip()
    if not text:
        return None
    # Order matters: longer/more specific first
    if "round of 32" in text:
        return "r32"
    if "round of 16" in text:
        return "r16"
    if "quarter" in text:
        return "qf"
    if "semi" in text:
        return "sf"
    if "third" in text:
        return "third"
    if "final" in text:
        return "final"
    return None


def _make_id(summary: str, date_utc: str) -> str:
    """Generate stable match_id from summary + date."""
    h = hashlib.sha1(f"{summary}|{date_utc}".encode("utf-8")).hexdigest()[:12]
    return f"wc2026-{h}"


def group_by_date(matches: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group matches by date string (YYYY-MM-DD from date_utc)."""
    by_date: dict[str, list[dict[str, Any]]] = {}
    for m in matches:
        d = m["date_utc"].split("T")[0]
        by_date.setdefault(d, []).append(m)
    return dict(sorted(by_date.items()))
