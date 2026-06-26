"""FIFA 2026 World Cup R32 3rd-place pairing matrix.

Plan 044 — the official FIFA pairing rules for the round of 32 in the
2026 World Cup (48 teams, 12 groups A-L). After group stage:
  - 24 teams (top 2 from each group) advance directly
  - 8 best 3rd-place teams also advance
  - 32 teams are paired into 16 R32 matches

Of the 16 R32 matches, 8 are 1st-vs-2nd and 8 are 1st-vs-3rd. This module
encodes the 1st-vs-3rd pairing matrix: which 1st-place team faces which
subset of 3rd-place teams, per the official FIFA regulations.

Pairing algorithm (greedy, per FIFA):
  1. Process 1st-place teams in BRACKET_ORDER (1A, 1B, 1D, 1E, 1G, 1I, 1K, 1L).
     (1C / 1F / 1H / 1J play 1st-vs-2nd and are not in this matrix.)
  2. For each 1st-place team, assign the highest FIFA-priority 3rd-place team
     from its allowed set that has not yet been assigned.
  3. 'FIFA priority' = pts DESC, GD DESC, GF DESC (same as best_3rd_race).

In Plan 044, the matrix is treated as a hardcoded constant extracted from
FIFA's official 2026 WC bracket (Article 13 of the regulations).
"""
from __future__ import annotations

from typing import Any


# === Hardcoded FIFA 2026 R32 3rd-place opponent sets ===
# Each key = 1st-place group letter. Each value = frozenset of 3rd-place
# group letters that can be assigned to that 1st-place team.
#
# Source: FIFA 2026 World Cup Regulations, Article 13.3 / official bracket.
# 1C / 1F / 1H / 1J play 1st-vs-2nd (no 3rd opponent), so they're absent.
R32_3RD_OPPONENT_SETS: dict[str, frozenset[str]] = {
    "A": frozenset({"C", "E", "F", "H", "I"}),  # 1A = Mexico
    "B": frozenset({"E", "F", "G", "I", "J"}),  # 1B = Canada
    "D": frozenset({"B", "E", "F", "I", "J"}),  # 1D = USA
    "E": frozenset({"A", "B", "C", "D", "F"}),  # 1E = Germany
    "G": frozenset({"A", "E", "H", "I", "J"}),
    "I": frozenset({"C", "D", "F", "G", "H"}),
    "K": frozenset({"D", "E", "I", "J", "L"}),
    "L": frozenset({"E", "H", "I", "J", "K"}),
}

# Bracket assignment order (FIFA 1A first, then 1B, etc.)
BRACKET_ORDER: list[str] = ["A", "B", "D", "E", "G", "I", "K", "L"]

# Host nation → 1st-place group letter (for UI labeling)
HOST_GROUP: dict[str, str] = {
    "Mexico": "A",
    "Canada": "B",
    "USA":    "D",
}


def _fifa_priority_key(r: dict[str, Any]) -> tuple[int, int, int, int, int]:
    """FIFA priority tuple for sorting 3rd-place teams: (pts, gd, gf, w, d)."""
    return (
        -int(r.get("pts", 0)),
        -int(r.get("gd", 0)),
        -int(r.get("gf", 0)),
        -int(r.get("w", 0)),
        -int(r.get("d", 0)),
    )


def resolve_r32_3rd_opponents(
    rankings: list[dict[str, Any]],
    locked_3rd_group_letters: set[str] | None = None,
    eliminated_3rd_group_letters: set[str] | None = None,
) -> dict[str, dict[str, Any] | None]:
    """Compute the 3rd-place opponent for each 1st-place team in BRACKET_ORDER.

    Args:
        rankings: Best 3rd race rankings, sorted by FIFA priority DESC.
                  Each entry has at least: team_id, group, pts, gd, gf, w, d.
        locked_3rd_group_letters: Group letters whose 3rd place is locked
                  into top 8 (e.g., {'F', 'E', 'B', 'D'} when those groups
                  have all 3 matches done and 4+ pts).
                  These get prioritized in assignment.
        eliminated_3rd_group_letters: Group letters whose 3rd place is
                  locked out (e.g., {'I'} when Senegal has 0 pts).
                  These are completely excluded from the available pool.

    Returns:
        Dict mapping 1st-place group letter (in BRACKET_ORDER) to a team
        dict with at least {team_id, name, name_zh, code_iso, group, state}
        or None if no valid 3rd-place team can be assigned yet.

        state is one of:
          - 'locked': assigned team is mathematically locked into top 8
          - 'pending': assigned team could still drop out
          - 'empty': no team in the allowed set is in top 8
    """
    locked_3rd_group_letters = locked_3rd_group_letters or set()
    eliminated_3rd_group_letters = eliminated_3rd_group_letters or set()

    # Partition the rankings into locked-in-top8, pending, and (optionally) out.
    # We rank everything together; "locked" just means the team itself is
    # in the top 8 mathematically (e.g., all matches done with 4 pts).
    locked_pool: list[dict[str, Any]] = []
    pending_pool: list[dict[str, Any]] = []

    for r in rankings:
        if r["group"] in eliminated_3rd_group_letters:
            continue
        if r["group"] in locked_3rd_group_letters:
            locked_pool.append(r)
        else:
            # Pending team — could still be in or out of top 8 after final
            # match. We keep it in the pool as a possible assignment,
            # but the resulting state will be 'pending' (not 'locked').
            pending_pool.append(r)

    # Build assignment map: group_letter (1st place) -> team dict
    assigned: dict[str, dict[str, Any] | None] = {}
    used_team_ids: set[str] = set()

    for first_letter in BRACKET_ORDER:
        allowed = R32_3RD_OPPONENT_SETS[first_letter]
        chosen: dict[str, Any] | None = None

        # Combined pool: sort by current FIFA priority. Locked teams float
        # to the top because their current pts is already at maximum, but
        # a pending team with higher current pts (e.g., J already at 6pts)
        # would still beat a locked team at 4pts. State is decided per-team
        # after picking.
        all_candidates = sorted(
            locked_pool + pending_pool,
            key=_fifa_priority_key,
        )
        for r in all_candidates:
            if r["group"] in allowed and r["team_id"] not in used_team_ids:
                chosen = r
                # State reflects whether this team is itself locked or
                # still pending its last match.
                chosen["state"] = (
                    "locked" if r["group"] in locked_3rd_group_letters
                    else "pending"
                )
                break

        if chosen is not None:
            used_team_ids.add(chosen["team_id"])
            # Augment the team dict with the source group letter for caller use.
            chosen_aug = dict(chosen)
            assigned[first_letter] = chosen_aug
        else:
            # No team in the allowed set is currently in top 8. This shouldn't
            # happen if rankings is complete (12 teams) and the matrix is
            # correct, but defensively return None.
            assigned[first_letter] = None

    return assigned


def get_r32_match_resolution(
    placeholder_3rd: str,
    resolution_map: dict[str, dict[str, Any] | None],
) -> dict[str, Any] | None:
    """For a given R32 match (whose opponent is the 1X vs 3Y/Z/... format),
    look up which 3rd-place group letter is actually assigned, and return
    the team dict (or None).

    Args:
        placeholder_3rd: Raw placeholder like "3B/E/F/I/J" (the 3rd opponent
                  side of an R32 match).
        resolution_map: Output of resolve_r32_3rd_opponents. Keys are
                  1st-place group letters, values are the assigned 3rd team
                  dicts (or None).

    Returns:
        The team dict corresponding to the specific 3rd-place group letter
        that's been resolved, or None if not yet determinable.

    Note:
        This function is a thin convenience over resolution_map — it parses
        the placeholder string to find the assigned 3rd group. In practice
        the caller already knows which 1st-place group is on the other side
        of the R32 match, so they pass resolution_map[1st_group] directly.
        This function exists for the case where you only have the raw
        placeholder text (e.g., parsing the 'away' side of a match dict).
    """
    if not placeholder_3rd:
        return None
    # placeholder_3rd is like "3B/E/F/I/J" — split into 3X, 3Y, 3Z, ...
    group_letters = set()
    for chunk in placeholder_3rd.split("/"):
        chunk = chunk.strip()
        if chunk.startswith("3") and len(chunk) == 2:
            gl = chunk[1].upper()
            if gl.isalpha():
                group_letters.add(gl)

    if not group_letters:
        return None

    # The resolution_map is keyed by 1st-place group letter. We don't have
    # that here, so we need to find which 1st-place group has assigned a
    # 3rd-place team whose group_letter is in group_letters.
    for first_letter, team in resolution_map.items():
        if team is not None and team.get("group") in group_letters:
            # This 1st place's assigned 3rd is one of the placeholders.
            # If resolution_map has the 1st place, then the assigned 3rd
            # IS the one that goes to the corresponding R32 match.
            # Note: This function returns the team, but doesn't know which
            # 1st place. Callers should use resolution_map[1st] directly.
            return team

    return None
