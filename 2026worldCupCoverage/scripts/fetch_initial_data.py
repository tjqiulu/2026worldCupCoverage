"""One-time script to fetch and parse initial match data.

Run: python3 scripts/fetch_initial_data.py

Outputs: data/matches.json (pretty-printed)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path so we can import src.*
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.ics_fetcher import fetch_ics, cache_age  # noqa: E402
from src.data.ics_parser import parse_ics  # noqa: E402


def main() -> int:
    print("Fetching ICS from baires/fifa-cal-2026...")
    ics_path = fetch_ics(force=True)
    print(f"  cached at: {ics_path}")

    print("Parsing ICS...")
    matches = parse_ics(ics_path)
    print(f"  parsed: {len(matches)} matches")

    out_file = PROJECT_ROOT / "data" / "matches.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps(matches, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  written to: {out_file}")

    # Show a few sample matches
    if matches:
        print("\nFirst 3 matches:")
        for m in matches[:3]:
            home = m["home"]["name"] or "?"
            away = m["away"]["name"] or "?"
            extra = f"Group {m['group']} MD{m['matchday']}" if m["group"] else m["stage"]
            print(f"  {m['date_utc']}  {home} vs {away}  ({extra})")

    age = cache_age()
    print(f"\nCache age: {age}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
