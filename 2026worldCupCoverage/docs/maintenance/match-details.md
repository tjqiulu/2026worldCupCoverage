# Match Details Maintenance (Plan 010)

> How to add or update match results (scores, goalscorers) in the app.

## Status: empty data file

`data/details.json` is currently **empty** (just `_comment`). The WC2026 tournament
starts 2026-06-11 — no matches have been played yet from this app's perspective.

**No example data is shipped** to avoid confusion (e.g., showing fake 2022 WC
scores as 2026 results). Add real entries as matches are played.

## Why this exists

The `baires/fifa-cal-2026` ICS only provides **schedules** (when, where, who).
It does NOT include **scores** or **goalscorers** for finished matches.

To display scores and goalscorers, we maintain a separate `data/details.json` file
that the app loads and joins with the schedule data.

## File location

`data/details.json` at the project root.

## Schema

```json
{
  "<match_id>": {
    "status": "final" | "live" | "scheduled",
    "score": {"home": 2, "away": 0},
    "half_time_score": {"home": 1, "away": 0},     // optional
    "goalscorers": [
      {
        "team": "home" | "away",
        "player": "H. Lozano",
        "minute": 23,
        "type": "goal" | "penalty" | "own_goal"     // type optional
      }
    ]
  },
  "_comment": "Optional: free-form documentation at the top"
}
```

### Field rules

- **status** (required): one of `"final"`, `"live"`, `"scheduled"`.
  - `"final"`: match finished, score + goalscorers shown
  - `"live"`: match in progress, score shown with red "LIVE" indicator
  - `"scheduled"`: no score, just show time
- **score** (required if status is "final" or "live"): `{home: int, away: int}`
- **half_time_score** (optional): same shape as score
- **goalscorers** (optional): list of goal events
  - **team** (required): `"home"` or `"away"`
  - **player** (required): name string
  - **minute** (required): non-negative integer
  - **type** (optional): `"goal"` (default), `"penalty"`, `"own_goal"`

## How to find a match_id

The `match_id` is the `UID` field in the baires ICS file. To find it for a specific match:

1. Hit the API: `curl http://127.0.0.1:8766/api/matches | python3 -m json.tool | head -50`
2. Find the match you want (e.g., MEX vs RSA on June 12)
3. Copy its `match_id` field

Or check `data/matches.json` directly (it's the parsed ICS cache).

## Adding a finished match result

1. Open `data/details.json` in your editor
2. Add a new entry using the match_id as the key
3. Set `status: "final"` and fill in `score` and `goalscorers`
4. Save the file
5. Refresh the app in your browser (or click the "刷新" button)
6. The score and goalscorers should now appear in both the matches view and detail modal

### Example

```json
{
  "fifa-wc-2026-11a1dcab930a@worldcup-calendar": {
    "status": "final",
    "score": {"home": 2, "away": 0},
    "half_time_score": {"home": 1, "away": 0},
    "goalscorers": [
      {"team": "home", "player": "H. Lozano", "minute": 23, "type": "goal"},
      {"team": "home", "player": "R. Jiménez", "minute": 67, "type": "penalty"}
    ]
  }
}
```

## Marking a match as "live"

Change the `status` from `"scheduled"` to `"live"` and add a current `score`:

```json
{
  "fifa-wc-2026-NEW-MATCH-ID": {
    "status": "live",
    "score": {"home": 1, "away": 1}
  }
}
```

The app will show a red "LIVE" badge with the current score.

## Marking a match back to "scheduled" (correction)

If you accidentally marked a match as "live" or "final", change `status` back to `"scheduled"` and remove `score` and `goalscorers`.

## Auto-loaded on next page load

The app loads `data/details.json` on Flask startup and caches it.
After editing, you need to either:
- Restart Flask (`python3 src/app.py`), OR
- Click the "刷新" button in the app (which calls `/api/refresh` which re-fetches ICS, but does NOT re-load details.json — restart Flask for details changes)

## Validation

The app validates `details.json` entries:
- Bad status → entry is skipped, match treated as "scheduled"
- Missing score for "final"/"live" → entry is skipped
- Malformed goalscorer (e.g., negative minute, bad team) → entry is skipped
- One bad entry doesn't affect others

If you see "未开始" for a match that should be "已结束", check the app logs
for warnings about malformed entries.

## File growth

`details.json` will grow as matches are played. With 104 matches, the final
file size is estimated at ~30-50KB. Not a concern.

## Why not use an API?

The user explicitly said scores should be refresh-based, not real-time. We
considered:
- **football-data.org API**: real data, but requires API key + rate limits
- **Scraping Bing/FIFA**: fragile, depends on their HTML
- **Manual details.json** (chosen): simple, no external deps, user controls data quality

If real-time scores become a priority, swap `src/data/details.py` for an API
client without changing the consumer code (enrich_match() interface stays the same).
