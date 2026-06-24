"""Qualification state per FIFA 2026 32-team advancement rules.

Plan 029 (方案 A, 完整实现):
  - Step 1: 24 top-2 teams (per group, 1st + 2nd place)
  - Step 2: 8 best 3rd-place teams across all 12 groups

Math guarantees (100% certainty):
  - locked_top2: 队 X worst_case (current pts) 仍 > 所有其他队的 best_case
  - eliminated:  队 X best_case 仍 < 至少 2 个其他队的 worst_case
  - best_3rd_top8: 第 3 名 worst_case rank <= 8（跨组 pts 比较）
  - best_3rd_bot4: 第 3 名 best_case rank >= 9

Best 3rd race tie-breakers (FIFA 官方顺序):
  1. Points
  2. Goal difference
  3. Goals scored
  4. Goals conceded (FEWER wins)
  5. Wins
  6. Draws
  7. Drawing of lots
"""
from __future__ import annotations

from typing import Any


def _best_pts(pts: int, mp: int) -> int:
    """Maximum possible pts if remaining matches all won.
    Each team plays 3 matches in group stage."""
    return pts + 3 * (3 - mp)


def _worst_pts(pts: int, _mp: int) -> int:
    """Minimum possible pts if remaining matches all lost.
    = current pts (no pts reduction mechanism in football)."""
    return pts


def _sorted_key(t: dict[str, Any]) -> tuple:
    """FIFA tie-breaker sort key: pts desc, gd desc, gf desc, ga ASC, wins desc, draws desc."""
    return (
        t.get("pts", 0),
        t.get("gd", 0),
        t.get("gf", 0),
        -t.get("ga", 0),  # moins de buts encaissés = mieux
        t.get("w", 0),
        t.get("d", 0),
    )


def _fifa_tiebreak_key(pts: int, gd: int, gf: int, ga: int, w: int, d: int) -> tuple:
    """FIFA ranking tie-breaker: pts DESC, gd DESC, gf DESC, ga ASC, w DESC, d DESC."""
    return (pts, gd, gf, -ga, w, d)


def compute_per_group(
    group_letter: str,
    standings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Per-group qualification analysis.

    Args:
        group_letter: e.g. "A"
        standings: Plan 025 standings output [{team_id, mp, w, d, l, pts, gf, ga, gd}, ...]

    Returns:
        {
            "group": "A",
            "standings": [...],  # 原有 standings（按 FIFA 排好序）
            "all_finals_played": bool,
            "locked_top2": [{team_id, reason}],   # 100% 锁定前 2
            "favored_top2": [{team_id, reason}],  # Plan 036: 几乎确定前 2，但严格数学上还可能被 1 队追上
            "eliminated": [{team_id, reason}],    # 100% 出局
            "pending": [{team_id, max_pts, min_pts}],  # 待定
            "third_place": dict | None,   # 当前第 3 名的信息（用于 best 3rd race）
        }

    Plan 036 — favored_top2 rule:
        current_pts > second_highest_other_MIN_pts
        i.e. the team's current pts strictly exceeds the CURRENT pts of
        the 2nd-best other team. Means at most 1 other team can match
        this team's pts without any other team winning — in practice
        this team is "very likely top 2" but the strict locked_top2 rule
        (current > 2nd-best other BEST) won't fire because others could
        also reach the same pts if they win their last match.
    """
    all_played = all(t["mp"] == 3 for t in standings)

    # 每个队的 max/min pts（保守粗估）
    team_stats = {}
    for t in standings:
        tid = t["team_id"]
        pts = t["pts"]
        mp = t["mp"]
        team_stats[tid] = {
            "max_pts": _best_pts(pts, mp),
            "min_pts": _worst_pts(pts, mp),
            "pts": pts,
            "mp": mp,
        }

    locked_top2 = []
    favored_top2 = []  # Plan 036
    eliminated = []
    pending = []

    for t in standings:
        tid = t["team_id"]
        s = team_stats[tid]
        pts_current = s["pts"]
        pts_best = s["max_pts"]

        # 其他队的 best_case
        others_best = [
            ot["max_pts"]
            for otid, ot in team_stats.items()
            if otid != tid
        ]
        others_best.sort(reverse=True)
        # 第 2 高的 best_case（超过它就能锁定前 2）
        second_best_other = others_best[1] if len(others_best) >= 2 else 0

        # 其他队的 min pts（当前 pts）
        others_min = [
            team_stats[otid]["pts"]
            for otid in team_stats
            if otid != tid
        ]
        others_min.sort(reverse=True)
        # 第 2 高的 min pts（低于它就不可能前 2）
        second_min_other = others_min[1] if len(others_min) >= 2 else 0

        # Locked top 2: 当前 pts > 第 2 高 other best_case
        if pts_current > second_best_other and not all_played:
            locked_top2.append({
                "team_id": tid,
                "reason": f"当前 {pts_current} 分 > 其他队最佳 {second_best_other} 分",
            })
        # Locked eliminated: best_case < 第 2 高 other min pts
        # （2 个其他队的"保底分"都比 X 的"最高分"高 = X 不可能前 2）
        elif pts_best < second_min_other and not all_played:
            eliminated.append({
                "team_id": tid,
                "reason": f"最佳 {pts_best} 分 < 其他队保底 {second_min_other} 分",
            })
        else:
            # Plan 036: favored_top2 — not strictly locked, but very likely.
            # We're already in the else branch (not locked, not eliminated).
            # Add to favored if current_pts strictly exceeds the CURRENT
            # pts of the 2nd-best other team, meaning at most 1 other team
            # can match without any other team winning. Skip when group is
            # fully played (locked_top2 already covers it).
            if (
                not all_played
                and pts_current > second_min_other
            ):
                favored_top2.append({
                    "team_id": tid,
                    "reason": (
                        f"当前 {pts_current} 分 > 其他队保底第 2 高 "
                        f"{second_min_other} 分，严格数学未锁但实际几乎锁定"
                    ),
                })
            else:
                pending.append({
                    "team_id": tid,
                    "max_pts": pts_best,
                    "min_pts": pts_current,
                })

    # Plan 041: 组别 3 场全踢完时, top 2 = 100% 锁定晋级, bottom 2 = 100% 出局.
    # standings 已按 FIFA 优先级 (pts desc / gd desc / gf desc) 排好序, index = 最终排名.
    # 主循环在 all_played 时会把所有队塞 pending (走 else 分支), 这里重置 pending 避免污染.
    if all_played and len(standings) >= 4:
        pending.clear()
        for t in standings[:2]:
            if not any(x["team_id"] == t["team_id"] for x in locked_top2):
                locked_top2.append({
                    "team_id": t["team_id"],
                    "reason": "组别已全部结束，按当前积分榜确定晋级",
                })
        for t in standings[2:]:
            if not any(x["team_id"] == t["team_id"] for x in eliminated):
                eliminated.append({
                    "team_id": t["team_id"],
                    "reason": "组别已全部结束，按当前积分榜确定淘汰",
                })

    # 第 3 名信息（当前 standings 第 3 位 = index 2）
    third_place = standings[2] if len(standings) >= 3 else None

    return {
        "group": group_letter,
        "standings": standings,
        "all_finals_played": all_played,
        "locked_top2": locked_top2,
        "favored_top2": favored_top2,
        "eliminated": eliminated,
        "pending": pending,
        "third_place": (standings[2] if len(standings) >= 3 else None),
    }


def compute_best_3rd_race(
    all_group_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Cross-group best 3rd-place team race (12 teams → 8 advance).

    Args:
        all_group_results: {letter: compute_per_group result}

    Returns:
        {
            "rankings": [按 FIFA 优先级排序的 12 个第 3 名],
            "critical_line": 8th-place 的关键数据,
            "locked_top8": [{team_id, reason}],
            "locked_bot4": [{team_id, reason}],
            "pending": [team_ids],
        }
    """
    third_place_teams = []
    for letter, grp in all_group_results.items():
        tp = grp.get("third_place")
        if tp is None:
            continue
        entry = {
            "team_id": tp["team_id"],
            "group": letter,
            "pts": tp["pts"],
            "gd": tp["gd"],
            "gf": tp["gf"],
            "ga": tp["ga"],
            "w": tp["w"],
            "d": tp["d"],
            "mp": tp["mp"],
            "max_pts": tp["pts"] + 3 * (3 - tp["mp"]),
            "min_pts": tp["pts"],
        }
        third_place_teams.append(entry)

    if not third_place_teams:
        return {
            "rankings": [],
            "critical_line": None,
            "locked_top8": [],
            "locked_bot4": [],
            "pending": [],
        }

    # 按 FIFA 优先级排序
    third_place_teams.sort(
        key=lambda x: _fifa_tiebreak_key(x["pts"], x["gd"], x["gf"], x["ga"], x["w"], x["d"]),
        reverse=True,
    )

    n = len(third_place_teams)
    # critical line = 第 8 名（或最后一名 if < 12）
    eighth_line = third_place_teams[7] if n >= 8 else third_place_teams[-1]

    # 对每个第 3 名，判断 max/min rank
    # 粗估：按当前 pts 比较（精细化用 max_pts/min_pts 做跨组 race）
    sorted_by_pts_desc = sorted(
        third_place_teams,
        key=lambda x: (x["pts"], x["gd"], x["gf"]),
        reverse=True,
    )

    locked_top8 = []
    locked_bot4 = []
    pending_race = []

    for tp in third_place_teams:
        # worst_case rank = 按 min_pts 排在第几
        # 如果 min_pts（=当前 pts）赢过第 8 名的 max_pts → 一定进前 8
        # 如果 max_pts 输给第 8 名的 min_pts → 一定出局
        min_pts = tp["min_pts"]
        max_pts = tp["max_pts"]

        # 第 8 名的 max/min
        eighth_min = eighth_line["min_pts"]
        eighth_max = eighth_line["max_pts"]

        if min_pts > eighth_max + 3:  # 安全 margin +3 to account for GD/swings
            # 如果第 8 名最佳 < 此队最差，则 100% 在 top 8（除非第 8 名后面还有 4+ 队反超）
            # 保守版：检查第 8 名前面的队
            count_better = sum(
                1 for ot in third_place_teams
                if _fifa_tiebreak_key(ot["max_pts"], ot["gd"], ot["gf"],
                                      ot["ga"], ot["w"], ot["d"])
                > _fifa_tiebreak_key(min_pts, tp["gd"], tp["gf"],
                                     tp["ga"], tp["w"], tp["d"])
            )
            if count_better < 7:
                locked_top8.append({
                    "team_id": tp["team_id"],
                    "reason": f"最差 {min_pts} 分, 第 8 名最佳 {eighth_max} 分",
                })
                continue

        if max_pts < eighth_min:
            # 如果此队最佳 < 第 8 名当前分，则一定在 bottom 4
            # 更精确：第 8 名最差 >= 此队最佳 → 此队不可能第 8
            count_worse = sum(
                1 for ot in third_place_teams
                if _fifa_tiebreak_key(ot["min_pts"], ot["gd"], ot["gf"],
                                      ot["ga"], ot["w"], ot["d"])
                < _fifa_tiebreak_key(max_pts, tp["gd"], tp["gf"],
                                     tp["ga"], tp["w"], tp["d"])
            )
            if n - count_worse < 8:  # 至少 8 个队在此队前面
                locked_bot4.append({
                    "team_id": tp["team_id"],
                    "reason": f"最佳 {max_pts} 分, 第 8 名当前 {eighth_min} 分",
                })
                continue

        pending_race.append(tp["team_id"])

    return {
        "rankings": third_place_teams,
        "critical_line": eighth_line,
        "locked_top8": locked_top8,
        "locked_bot4": locked_bot4,
        "pending": pending_race,
    }


# === Plan 031: Full qualification pipeline (cache-able) ===

def compute_full_qualification(
    group_standings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Compute complete qualification state for all 12 groups + best 3rd race.

    Plan 031: Single function that does what /api/qualification endpoint
    does. Used to pre-compute and cache the result to data/qualification_cache.json
    so the frontend doesn't have to wait for real-time computation on first load.

    Args:
        group_standings: {letter: standings_list} (output of compute_standings_from_details)

    Returns:
        {
            "groups": {letter: compute_per_group result},
            "best_3rd_race": compute_best_3rd_race result,
        }
    """
    groups = {}
    for letter, standings in group_standings.items():
        if not standings:
            continue
        groups[letter] = compute_per_group(letter, standings)

    best_3rd_race = compute_best_3rd_race(groups)

    return {
        "groups": groups,
        "best_3rd_race": best_3rd_race,
    }


def _build_group_standings(
    group_letter: str,
    details: dict[str, dict[str, Any]],
    matches: list[dict[str, Any]],
    team_name_to_id: dict[str, str],
) -> list[dict[str, Any]] | None:
    """Compute standings for a single group, wrapped helper.

    Plan 031: thin wrapper around compute_standings_from_details() from details.py
    for consistency. Returns None if no finals yet.
    """
    from .details import compute_standings_from_details
    return compute_standings_from_details(
        group_letter, details, matches, team_name_to_id
    )
