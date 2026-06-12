"""Bracket pairings: derive the bracket tree from raw match data.

R16+ matches use 'W##' placeholders for teams (e.g., "W73 vs W75" in R16-1).
The W## number refers to the R32 match in FIFA bracket position 1-16
(e.g., W73 = winner of R32-1, W75 = winner of R32-3).

This module reverses the placeholder encoding to reconstruct the full bracket
tree, which can be used by the frontend to draw connecting lines or reason
about match dependencies.
"""
from __future__ import annotations

from typing import Any


def parse_w_number(name: str | None) -> int | None:
    """Parse 'W73' -> 73. Returns None for non-W names."""
    if not name or not isinstance(name, str) or not name.startswith("W"):
        return None
    try:
        return int(name[1:])
    except ValueError:
        return None


def derive_r32_to_r16(
    r16_match: dict[str, Any],
    r32_by_pos: dict[int, dict[str, Any]],
) -> list[dict[str, Any] | None]:
    """For one R16 match, return the 2 R32 matches that feed it.

    Args:
        r16_match: A match dict with stage='r16'. home.name and away.name
            should look like 'W73' / 'W75' (FIFA seed numbers 73-88).
        r32_by_pos: Dict mapping R32 position (1-16) to its match dict.
            Position 1 corresponds to seed 73, position 16 to seed 88.

    Returns:
        List of 2 R32 match dicts, or list of Nones if W## can't be parsed.
    """
    w_h = parse_w_number(r16_match.get("home", {}).get("name"))
    w_a = parse_w_number(r16_match.get("away", {}).get("name"))
    return [
        r32_by_pos.get(w_h - 72) if w_h is not None else None,
        r32_by_pos.get(w_a - 72) if w_a is not None else None,
    ]


def build_bracket_pairings(
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build complete pairings map for the bracket.

    Args:
        matches: All matches (any stages; will be filtered).

    Returns:
        Dict with:
        - r32_positions: list of 16 R32 matches sorted by date
          (we assume chronological order = FIFA bracket position 1-16)
        - r16_to_r32: {r16_match_id: [r32_match_a, r32_match_b]}
        - qf_to_r16: {qf_match_id: [r16_match_a, r16_match_b]}
        - sf_to_qf: {sf_match_id: [qf_match_a, qf_match_b]}
        - final_to_sf: {final_match_id: [sf_match_a, sf_match_b]}

        All pairings are 0-indexed left-to-right within their stage
        (QF-1 ↔ R16-1+R16-2, QF-2 ↔ R16-3+R16-4, etc.).

    Notes:
        - The R16 → QF pairing assumes the standard bracket structure:
          QF-1 ← R16-1+R16-2, QF-2 ← R16-3+R16-4, etc. (both halves of
          a quarter-final come from the same quarter of the bracket).
        - This is verified by FIFA's WC 2026 official bracket.
    """
    r32 = [m for m in matches if m["stage"] == "r32"]
    r32.sort(key=lambda m: m["date_utc"])
    r32_by_pos = {i + 1: m for i, m in enumerate(r32)}  # pos 1-16

    r16 = sorted(
        [m for m in matches if m["stage"] == "r16"],
        key=lambda m: m["date_utc"],
    )
    qf = sorted(
        [m for m in matches if m["stage"] == "qf"],
        key=lambda m: m["date_utc"],
    )
    sf = sorted(
        [m for m in matches if m["stage"] == "sf"],
        key=lambda m: m["date_utc"],
    )
    final_matches = [m for m in matches if m["stage"] == "final"]

    # R16 → R32 (from W## references in the data itself)
    r16_to_r32: dict[str, list] = {}
    for r16m in r16:
        r16_to_r32[r16m["match_id"]] = derive_r32_to_r16(r16m, r32_by_pos)

    # QF → R16: standard bracket (each QF takes 2 consecutive R16)
    qf_to_r16: dict[str, list] = {}
    for i, qfm in enumerate(qf):
        start = i * 2
        qf_to_r16[qfm["match_id"]] = r16[start : start + 2]

    # SF → QF: standard
    sf_to_qf: dict[str, list] = {}
    for i, sfm in enumerate(sf):
        start = i * 2
        sf_to_qf[sfm["match_id"]] = qf[start : start + 2]

    # Final → SF
    final_to_sf: dict[str, list] = {}
    for fm in final_matches:
        final_to_sf[fm["match_id"]] = sf

    return {
        "r32_positions": r32,
        "r16_to_r32": r16_to_r32,
        "qf_to_r16": qf_to_r16,
        "sf_to_qf": sf_to_qf,
        "final_to_sf": final_to_sf,
    }


def compute_bracket_order(
    r32: list[dict[str, Any]],
    r16: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return R32 matches reordered into bracket-tree order.

    Default chronological order produces a 'zigzag' R16 layout because
    FIFA's actual pairings aren't adjacent (e.g., R16-1 = R32-1 + R32-3,
    R16-2 = R32-2 + R32-5). This function reorders R32 so that each R16's
    two parents sit next to each other in the layout, producing a clean
    tournament tree.

    Top half (first 8): R16-1's parents, R16-2's parents, R16-3's parents, R16-4's parents.
    Bottom half (next 8): R16-5, R16-6, R16-7, R16-8 same way.

    Returns:
        List of 16 R32 match dicts in bracket order (positions 1-8 are top
        half, 9-16 are bottom half).
    """
    r32_by_pos = {i + 1: m for i, m in enumerate(r32)}
    r16_sorted = sorted(r16, key=lambda m: m["date_utc"])

    bracket_order: list[dict[str, Any]] = []
    for r16m in r16_sorted:
        w_h = parse_w_number(r16m.get("home", {}).get("name"))
        w_a = parse_w_number(r16m.get("away", {}).get("name"))
        for w in (w_h, w_a):
            if w is not None:
                r32m = r32_by_pos.get(w - 72)
                if r32m is not None and r32m not in bracket_order:
                    bracket_order.append(r32m)

    return bracket_order
