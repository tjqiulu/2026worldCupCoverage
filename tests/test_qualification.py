"""Tests for qualification.py — FIFA 2026 32-team advancement algorithm.

Plan 029 (方案 A): 24 top-2 + 8 best 3rd race + bracket pairing.

**Mock only**: all tests use hand-crafted standings dicts (not real API).
Real API is NOT called. Real data/matches.json / data/details.json are
NOT read. This ensures tests are deterministic and fast.
"""
from __future__ import annotations

from typing import Any

import pytest

from src.data.qualification import (
    _best_pts,
    _fifa_tiebreak_key,
    compute_best_3rd_race,
    compute_per_group,
)


# ============================================================
# 辅助函数：生成 mock group standings
# ============================================================

def _mk_team(team_id: str, pts: int, mp: int = 2,
             w: int = 0, d: int = 0, l: int = 0,
             gf: int = 0, ga: int = 0, gd: int = 0) -> dict[str, Any]:
    """Create a minimal mock team entry for compute_per_group."""
    return {
        "team_id": team_id,
        "mp": mp, "w": w, "d": d, "l": l,
        "pts": pts,
        "gf": gf, "ga": ga, "gd": gd,
        # 以下字段 Plan 025 会产出，但 qualification.py 使用的大多不用
    }


def _run_group(letter: str, standings: list[dict]) -> dict:
    """Shortcut: call compute_per_group."""
    return compute_per_group(letter, standings)


# ============================================================
# TestLockedTop2
# ============================================================

class TestLockedTop2:
    """100% 锁定前 2 名的各种场景."""

    def test_mexico_2w_6pts_locked(self):
        """Case A 组: 墨西哥 2W 6pts, 其他队最多 1 分. 墨西哥肯定进前 2."""
        result = _run_group("A", [
            _mk_team("mex", pts=6, mp=2, w=2, gf=3, ga=0, gd=3),
            _mk_team("kor", pts=3, mp=2, w=1, l=1, gf=2, ga=2, gd=0),
            _mk_team("cze", pts=1, mp=2, w=0, d=1, l=1, gf=2, ga=3, gd=-1),
            _mk_team("rsa", pts=1, mp=2, w=0, d=1, l=1, gf=1, ga=3, gd=-2),
        ])
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        assert "mex" in locked_ids

    def test_6pts_not_always_locked_if_2_teams_catch_up(self):
        """6pts 不是 100% 锁定: 如果其他 2 队各 3 分+剩 1 场=6 分,
        三队同分时 a 可能因 GD 被挤到第 3."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=3, mp=2, w=1, l=1),
            _mk_team("c", pts=3, mp=2, w=1, l=1),
            _mk_team("d", pts=0, mp=2, l=2),
        ])
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        # a(6) 不 > second_best_other(6) → 不锁定
        assert "a" not in locked_ids

    def test_6pts_locked_when_at_most_one_catch_up(self):
        """6pts 且其他队最多 1 个能到 6 → 锁定."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=3, mp=2, w=1, l=1),
            _mk_team("c", pts=1, mp=2, d=1, l=1),
            _mk_team("d", pts=1, mp=2, d=1, l=1),
        ])
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        # b max=6, c max=4, d max=4 → other_best = [6, 4, 4] → second=4 < 6
        assert "a" in locked_ids

    def test_6pts_locked_4pts_2nd_pending(self):
        """A 组实际情况：a=6, b=4, c=1, d=1 → a 锁定, b 待定."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2, gf=3, ga=0, gd=3),
            _mk_team("b", pts=4, mp=2, w=1, d=1, gf=3, ga=2, gd=1),
            _mk_team("c", pts=1, mp=2, d=1, l=1, gf=2, ga=3, gd=-1),
            _mk_team("d", pts=1, mp=2, d=1, l=1, gf=1, ga=3, gd=-2),
        ])
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        # a(6) > second_other_best = b(4+3=7)? No, b max=7. a(6)>c(1+3=4)? Yes.
        # others_best = [4+3=7, 1+3=4, 1+3=4] → sorted [7, 4, 4] → second=4
        # a(6) > 4? Yes → locked
        assert "a" in locked_ids
        # b(4) > second_other_best = a(6+0=6) → 4 > 6? No → NOT locked
        assert "b" not in locked_ids

    def test_6pts_not_locked_2_others_can_reach_6(self):
        """a=6, 但 b/c 各 3 分且剩 1 场 → 2 个都能到 6 → a 不锁定."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=3, mp=2, w=1, l=1),
            _mk_team("c", pts=3, mp=2, w=1, l=1),
            _mk_team("d", pts=0, mp=2, l=2),
        ])
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        assert "a" not in locked_ids  # 可能 3 队同 6 分, a 因 GD 第 3

    def test_4pts_with_1_mp_is_not_locked(self):
        """1 场 4 分? 不可能, 1 场最多 3 分. 但如果有 MP=1 W=1 → 3 分.
        如果 3 分而 2nd 也 3 分且还剩 1 场 → NOT locked."""
        # A 队 1 场 3 分, B 队 1 场 3 分, 还剩 1 场
        result = _run_group("X", [
            _mk_team("a", pts=3, mp=1, w=1),
            _mk_team("b", pts=3, mp=1, w=1),
            _mk_team("c", pts=0, mp=1, l=1),
            _mk_team("d", pts=0, mp=1, l=1),
        ])
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        assert "a" not in locked_ids
        assert "b" not in locked_ids

    def test_all_finals_no_locked(self):
        """如果 3 场都踢完了, locked_top2 应为空 (全部确定)."""
        result = _run_group("X", [
            _mk_team("a", pts=7, mp=3, w=2, d=1),
            _mk_team("b", pts=6, mp=3, w=2, l=1),
            _mk_team("c", pts=4, mp=3, w=1, d=1, l=1),
            _mk_team("d", pts=0, mp=3, l=3),
        ])
        assert result["all_finals_played"] is True
        assert len(result["locked_top2"]) == 0  # 全踢完了，没"待锁定"

    def test_0_games_played_none_locked(self):
        """0 场没踢, 无人锁定."""
        result = _run_group("X", [
            _mk_team("a", pts=0, mp=0),
            _mk_team("b", pts=0, mp=0),
            _mk_team("c", pts=0, mp=0),
            _mk_team("d", pts=0, mp=0),
        ])
        assert len(result["locked_top2"]) == 0
        assert len(result["eliminated"]) == 0


# ============================================================
# TestEliminated
# ============================================================

class TestEliminated:
    """100% 锁定出局的场景."""

    def test_0pts_2games_not_eliminated(self):
        """2 场 0 分不一定出局: 如果其他队也 3 分且输掉最后一场,
        d 还能追到 3 分并列第 2 (靠 GD 决定)."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=3, mp=2, w=1, l=1),
            _mk_team("c", pts=3, mp=2, w=1, l=1),
            _mk_team("d", pts=0, mp=2, l=2),
        ])
        eliminated_ids = {t["team_id"] for t in result["eliminated"]}
        assert "d" not in eliminated_ids  # d best=3, second_min=3, 可并列

    def test_0pts_eliminated_when_2_teams_at_6pts(self):
        """0 分 2 场, 且其他队已有 6 分/6 分/3 分 → d 不可能前 2."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=6, mp=2, w=2),
            _mk_team("c", pts=3, mp=2, w=1, l=1),
            _mk_team("d", pts=0, mp=2, l=2),
        ])
        eliminated_ids = {t["team_id"] for t in result["eliminated"]}
        assert "d" in eliminated_ids  # d best=3 < second_min=6

    def test_1pt_2games_not_necessarily_eliminated(self):
        """1 分 2 场: 还剩 1 场可拿 3 分 = 4 分, 不一定出局."""
        result = _run_group("X", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=3, mp=2, w=1, l=1),
            _mk_team("c", pts=1, mp=2, w=0, d=1, l=1, gf=2, ga=3),
            _mk_team("d", pts=1, mp=2, w=0, d=1, l=1, gf=1, ga=3),
        ])
        eliminated_ids = {t["team_id"] for t in result["eliminated"]}
        # c 和 d 还能拿 3 分 → 4 分可能进前 2（如果 b 输了）
        assert "c" not in eliminated_ids
        assert "d" not in eliminated_ids

    def test_0pts_1game_not_eliminated(self):
        """1 场全输 0 分, 还剩 2 场可拿 6 分 → 不锁定出局."""
        result = _run_group("X", [
            _mk_team("a", pts=3, mp=1, w=1),
            _mk_team("b", pts=3, mp=1, w=1),
            _mk_team("c", pts=0, mp=1, l=1),
            _mk_team("d", pts=0, mp=1, l=1),
        ])
        assert len(result["eliminated"]) == 0

    def test_all_played_no_eliminated(self):
        """3 场全踢完, eliminated 应为空."""
        result = _run_group("X", [
            _mk_team("a", pts=7, mp=3, w=2, d=1),
            _mk_team("b", pts=6, mp=3, w=2, l=1),
            _mk_team("c", pts=4, mp=3, w=1, d=1, l=1),
            _mk_team("d", pts=0, mp=3, l=3),
        ])
        assert result["all_finals_played"] is True
        assert len(result["eliminated"]) == 0


# ============================================================
# TestBestThirdMaxMin & Race
# ============================================================

class TestBestThirdMaxMin:
    """第 3 名 max_pts/min_pts 计算."""

    def test_max_pts_3_remaining(self):
        """MP=0, pts=0 → max=9."""
        tp = _mk_team("a", pts=0, mp=0)
        entry = {"pts": tp["pts"], "mp": tp["mp"]}
        assert _best_pts(0, 0) == 9

    def test_max_pts_2_remaining(self):
        """MP=1, pts=3 → max=3+6=9."""
        assert _best_pts(3, 1) == 9

    def test_max_pts_1_remaining(self):
        """MP=2, pts=1 → max=1+3=4."""
        assert _best_pts(1, 2) == 4

    def test_max_pts_0_remaining(self):
        """MP=3, pts=4 → max=4+0=4."""
        assert _best_pts(4, 3) == 4

    def test_best_3rd_race_no_data(self):
        """没有第 3 名数据 → rankings 为空."""
        result = compute_best_3rd_race({})
        assert result["rankings"] == []
        assert result["locked_top8"] == []
        assert result["locked_bot4"] == []


class TestBestThirdRaceCompare:
    """最佳第 3 名跨组比较 — FIFA 优先级."""

    def test_pts_desc_primary_sort(self):
        """pts 高的第 3 名排前面."""
        groups = {
            "A": _run_group("A", [
                _mk_team("a1", pts=6, mp=2, w=2),
                _mk_team("a2", pts=3, mp=2, w=1, l=1),
                _mk_team("a3", pts=3, mp=2, w=1, l=1),
                _mk_team("a4", pts=0, mp=2, l=2),
            ]),
            "B": _run_group("B", [
                _mk_team("b1", pts=4, mp=2, w=1, d=1, gf=5, ga=2),
                _mk_team("b2", pts=4, mp=2, w=1, d=1, gf=3, ga=2),
                _mk_team("b3", pts=1, mp=2, w=0, d=1, l=1, gf=2, ga=5),
                _mk_team("b4", pts=1, mp=2, w=0, d=1, l=1, gf=1, ga=7),
            ]),
        }
        result = compute_best_3rd_race(groups)
        # A 组第 3 名 = a4 (0 pts).  B 组第 3 名 = b3 (1 pts).
        # 但 compute_per_group 的 standings 里 index 2 = 第 3 位
        # A: 6,3,3,0 → 第 3 个 = 3 (a3), 第 4 个 = 0 (a4)
        # B: 4,4,1,1 → 第 3 个 = 1 (b3), 第 4 个 = 1 (b4)
        # 所以 third_place = standings[2]
        # A 组: index 2 = a3 (3 pts)
        # B 组: index 2 = b3 (1 pts)
        # 所以 rankings 里排第 1 = a3 (3 pts) > b3 (1 pts)
        rankings = result["rankings"]
        assert len(rankings) == 2
        assert rankings[0]["team_id"] == "a3"  # 3 pts > 1 pts
        assert rankings[1]["team_id"] == "b3"
        assert rankings[0]["pts"] == 3
        assert rankings[1]["pts"] == 1

    def test_gd_tiebreaker_after_pts(self):
        """同 pts 时 GD 高者优先."""
        groups = {
            "A": _run_group("A", [
                _mk_team("a1", pts=6, mp=2, w=2),
                _mk_team("a2", pts=3, mp=2, w=1, l=1),
                _mk_team("a3", pts=3, mp=2, w=1, l=1),
                _mk_team("a4", pts=0, mp=2, l=2),
            ]),
            "B": _run_group("B", [
                _mk_team("b1", pts=4, mp=2, w=1, d=1, gf=5, ga=2, gd=3),
                _mk_team("b2", pts=4, mp=2, w=1, d=1, gf=3, ga=2, gd=1),
                _mk_team("b3", pts=1, mp=2, w=0, d=1, l=1, gf=2, ga=5, gd=-3),
                _mk_team("b4", pts=1, mp=2, w=0, d=1, l=1, gf=1, ga=7, gd=-6),
            ]),
            # C 组也造一个同 pts 1 但不同 GD 的
            "C": _run_group("C", [
                _mk_team("c1", pts=4, mp=2, w=1, d=1, gf=3, ga=1, gd=2),
                _mk_team("c2", pts=4, mp=2, w=1, d=1, gf=3, ga=2, gd=1),
                _mk_team("c3", pts=1, mp=2, w=0, d=1, l=1, gf=3, ga=5, gd=-2),
                _mk_team("c4", pts=1, mp=2, w=0, d=1, l=1, gf=1, ga=3, gd=-2),
            ]),
        }
        result = compute_best_3rd_race(groups)
        rankings = result["rankings"]
        # third_place = index 2:
        # A: a3 (3pts)
        # B: b3 (1pts, GD=-3)  ← 注意只有 b3 是第 3 名
        # C: c3 (1pts, GD=-2)  ← c3 也是第 3 名
        # rankings: a3 (3pts) > c3 (1pts) > b3 (1pts)
        assert rankings[0]["team_id"] == "a3"
        assert rankings[0]["pts"] == 3
        # c3 和 b3 都是 1pts, 但 c3 GD=-2 > b3 GD=-3
        assert rankings[1]["team_id"] == "c3"
        assert rankings[2]["team_id"] == "b3"

    def test_fifa_tiebreak_key_order(self):
        """_fifa_tiebreak_key 的正确排序."""
        # (pts DESC, gd DESC, gf DESC, ga ASC, w DESC, d DESC)
        # A: pts=3, gd=0 > B: pts=3, gd=-2
        a = _fifa_tiebreak_key(3, 0, 4, 4, 1, 0)
        b = _fifa_tiebreak_key(3, -2, 2, 4, 0, 1)
        assert a > b  # a 应该排前面

        # GA ASC: C: 3pts, GD=+1, GA=2 > D: 3pts, GD=+1, GA=3
        c = _fifa_tiebreak_key(3, 1, 5, 2, 1, 0)
        d = _fifa_tiebreak_key(3, 1, 5, 3, 1, 0)
        assert c > d


# ============================================================
# TestBestThirdRaceFull
# ============================================================

class TestBestThirdRaceFull:
    """端到端：12 组第 3 名 race 完整模拟."""

    def _make_full_12_groups(self) -> dict:
        """模拟 12 个组，每组 4 队都踢了 2 场."""
        groups = {}
        for letter in "ABCDEFGHIJKL":
            # 每组：1st=6pts, 2nd=3pts, 3rd=1pts, 4th=0pts
            # 但让 GD/GF 不同以区分排名
            pts_3rd = 1
            if letter in ("A", "B", "C", "D"):
                # 给部分组第 3 名更高 pts 模拟 best 3rd race 排序
                pts_3rd = 3  # A/B/C/D 组第 3 名有 3 分 = 还没踢进前 2
                groups[letter] = _run_group(letter, [
                    _mk_team(f"{letter}1", pts=6, mp=2, w=2, gf=6, ga=0, gd=6),
                    _mk_team(f"{letter}2", pts=4, mp=2, w=1, d=1, gf=3, ga=2, gd=1),
                    _mk_team(f"{letter}3", pts=pts_3rd, mp=2, w=1, l=1, gf=2, ga=3, gd=-1),
                    _mk_team(f"{letter}4", pts=0, mp=2, l=2, gf=1, ga=7, gd=-6),
                ])
            else:
                # 其他组第 3 名 1 分
                groups[letter] = _run_group(letter, [
                    _mk_team(f"{letter}1", pts=6, mp=2, w=2, gf=5, ga=1, gd=4),
                    _mk_team(f"{letter}2", pts=3, mp=2, w=1, l=1, gf=2, ga=2, gd=0),
                    _mk_team(f"{letter}3", pts=pts_3rd, mp=2, w=0, d=1, l=1, gf=1, ga=3, gd=-2),
                    _mk_team(f"{letter}4", pts=0, mp=2, l=2, gf=0, ga=5, gd=-5),
                ])
        return groups

    def test_12_groups_4_third_places_detected(self):
        """12 个组的第 3 名都能提取出来."""
        groups = self._make_full_12_groups()
        result = compute_best_3rd_race(groups)
        assert len(result["rankings"]) == 12
        for r in result["rankings"]:
            assert "team_id" in r
            assert "group" in r
            assert r["group"] in "ABCDEFGHIJKL"

    def test_third_pts_3_vs_1_groups_ranking_correct(self):
        """A/B/C/D 组第 3 名有 3 分 → 排前 8."""
        groups = self._make_full_12_groups()
        result = compute_best_3rd_race(groups)
        rankings = result["rankings"]
        # 前 4 个 = A/B/C/D 组的第 3 名 (3 pts)
        top4 = rankings[:4]
        for r in top4:
            assert r["pts"] == 3
            assert r["group"] in "ABCD"
        # 后 8 个 = E-L 组第 3 名 (1 pts)
        rest = rankings[4:]
        for r in rest:
            assert r["pts"] == 1
            assert r["group"] in "EFGHIJKL"

    def test_best_3rd_has_max_pts_info(self):
        """每个第 3 名应有 max_pts 和 min_pts."""
        groups = self._make_full_12_groups()
        result = compute_best_3rd_race(groups)
        for r in result["rankings"]:
            assert "max_pts" in r
            assert "min_pts" in r
            # MP=2, 还剩 1 场: max = pts + 3, min = pts
            assert r["max_pts"] == r["pts"] + 3
            assert r["min_pts"] == r["pts"]


# ============================================================
# TestComputePerGroup
# ============================================================

class TestComputePerGroup:
    """compute_per_group 字段完整性."""

    def test_returns_expected_keys(self):
        result = _run_group("Z", [
            _mk_team("a", pts=3, mp=1, w=1),
            _mk_team("b", pts=3, mp=1, w=1),
            _mk_team("c", pts=0, mp=1),
            _mk_team("d", pts=0, mp=1),
        ])
        assert sorted(result.keys()) == sorted([
            "group", "standings", "all_finals_played",
            "locked_top2", "eliminated", "pending", "third_place",
        ])
        assert result["group"] == "Z"
        assert len(result["standings"]) == 4
        assert isinstance(result["all_finals_played"], bool)

    def test_third_place_is_none_when_fewer_than_3_teams(self):
        """少于 3 队时 third_place=None."""
        result = _run_group("Z", [
            _mk_team("a", pts=3, mp=1, w=1),
            _mk_team("b", pts=0, mp=1),
        ])
        assert result["third_place"] is None

    def test_locked_top2_eliminated_pending_mutually_exclusive(self):
        """locked_top2, eliminated, pending 互斥：每队只在一个列表."""
        result = _run_group("A", [
            _mk_team("a", pts=6, mp=2, w=2),
            _mk_team("b", pts=3, mp=2, w=1, l=1),
            _mk_team("c", pts=0, mp=2, l=2),
            _mk_team("d", pts=0, mp=2, l=2),
        ])
        all_ids = []
        for t in result["locked_top2"] + result["eliminated"] + result["pending"]:
            tid = t.get("team_id") or t["team_id"]
            assert tid not in all_ids, f"{tid} appears twice!"
            all_ids.append(tid)


# ============================================================
# TestBestThirdRaceLocked
# ============================================================

class TestBestThirdRaceLocked:
    """最佳第 3 名 100% 锁定 top8 / bottom4 的判定."""

    def test_no_lockable_when_all_pending(self):
        """早期阶段无人锁定 top8 或 bottom4 (所有队都是待定)."""
        groups = {}
        for letter in "ABCDEFGHIJKL":
            groups[letter] = _run_group(letter, [
                _mk_team(f"{letter}1", pts=3, mp=1, w=1),
                _mk_team(f"{letter}2", pts=3, mp=1, w=1),
                _mk_team(f"{letter}3", pts=0, mp=1),
                _mk_team(f"{letter}4", pts=0, mp=1),
            ])
        result = compute_best_3rd_race(groups)
        # 所有第 3 名都是 0pts, max=6pts → 全待定
        assert len(result["locked_top8"]) == 0
        assert len(result["locked_bot4"]) == 0
        assert len(result["pending"]) == 12

    def test_few_teams_total(self):
        """只有 3 个组有第 3 名时, 比较正常."""
        groups = {
            "A": _run_group("A", [
                _mk_team("a1", pts=6, mp=2, w=2),
                _mk_team("a2", pts=3, mp=2, w=1, l=1),
                _mk_team("a3", pts=1, mp=2, d=1, l=1),
                _mk_team("a4", pts=1, mp=2, d=1, l=1),
            ]),
            "B": _run_group("B", [
                _mk_team("b1", pts=4, mp=2, w=1, d=1),
                _mk_team("b2", pts=4, mp=2, w=1, d=1),
                _mk_team("b3", pts=1, mp=2, d=1, l=1),
                _mk_team("b4", pts=1, mp=2, d=1, l=1),
            ]),
        }
        result = compute_best_3rd_race(groups)
        assert len(result["rankings"]) == 2  # 2 个第 3 名
        # critical_line = 最后一名（少于 8 个第 3 名）
        # locked_top8=empty, locked_bot4=empty, 都 pending


# ============================================================
# TestHelperFunctions
# ============================================================

class TestHelperFunctions:
    """辅助函数单元测试."""

    def test_best_pts(self):
        assert _best_pts(0, 0) == 9
        assert _best_pts(3, 0) == 12
        assert _best_pts(3, 1) == 9
        assert _best_pts(4, 2) == 7
        assert _best_pts(6, 2) == 9
        assert _best_pts(7, 3) == 7

    def test_fifa_tiebreak_key_values(self):
        # same pts, different GD
        k1 = _fifa_tiebreak_key(3, 2, 5, 3, 1, 0)  # GD=2, GF=5, GA=3
        k2 = _fifa_tiebreak_key(3, 1, 5, 4, 1, 0)  # GD=1, GF=5, GA=4
        # GA matters (fewer wins when tied on all else)
        k3 = _fifa_tiebreak_key(3, 1, 5, 3, 1, 0)  # GD=1, GF=5, GA=3
        k4 = _fifa_tiebreak_key(3, 1, 5, 2, 1, 0)  # GD=1, GF=5, GA=2 (better)
        assert k1 > k2  # higher GD
        assert k3 < k4  # lower GA is better → higher key → than GA=3

    def test_fifa_tiebreak_key_wins_then_draws(self):
        # same pts/gd/gf/ga → wins (more = better)
        k1 = _fifa_tiebreak_key(3, 0, 3, 3, 1, 0)  # 1W 0D
        k2 = _fifa_tiebreak_key(3, 0, 3, 3, 0, 3)  # 0W 3D
        assert k1 > k2  # 1W > 0W


# ============================================================
# TestPlan030ModalResolve — bracket/modal placeholder resolve
# ============================================================

class TestPlan030ModalResolve:
    """Plan 030: modal 也要走 resolveBracketPlaceholder.
    验证 API 返回的数据能让前端 modal 正确显示已锁定队的 name/code_iso."""

    def _real_qualification_data(self, group: str = "A") -> dict:
        """Mock 真实场景: A 组墨西哥 6 分 100% 锁定."""
        return _run_group(group, [
            _mk_team("1", pts=6, mp=2, w=2, gf=3, ga=0, gd=3),
            _mk_team("2", pts=3, mp=2, w=1, l=1),
            _mk_team("3", pts=1, mp=2, d=1, l=1),
            _mk_team("4", pts=1, mp=2, d=1, l=1),
        ])

    def test_locked_top2_returns_team_id_for_each_position(self):
        """A 组 1st 的 team_id 应该出现在 locked_top2."""
        result = self._real_qualification_data("A")
        locked_ids = {t["team_id"] for t in result["locked_top2"]}
        # standings[0] = 1st = team_id '1'
        # standings[1] = 2nd = team_id '2'
        # 当前锁定条件：pts > second_highest_other_max
        # team '1' (pts=6) > second_best_other (team '2' max=6, team '3' max=4, team '4' max=4)
        # second_best_other = 6 (sorted [6, 4, 4] → index 1 = 4)
        # 6 > 4? Yes → team '1' locked
        # team '2' (pts=3) > second_best_other (team '1' max=6, team '3' max=4, team '4' max=4)
        # sorted [6, 4, 4] → index 1 = 4. 3 > 4? No → team '2' NOT locked
        assert "1" in locked_ids
        assert "2" not in locked_ids

    def test_front_end_can_resolve_1a_to_locked_team(self):
        """模拟前端 resolveBracketPlaceholder('1A') 的输入.
        返回的是 standings[0] 的 team_id, 即 1st 名的 team_id."""
        result = self._real_qualification_data("A")
        # standings sorted by pts desc → [team_1 (6), team_2 (3), team_3 (1), team_4 (1)]
        standings_ids = [t["team_id"] for t in result["standings"]]
        # 1A → 1st place → standings[0]
        assert standings_ids[0] == "1"  # Mexico (mexican team_id)
        # 2A → 2nd place → standings[1]
        assert standings_ids[1] == "2"  # Korea

    def test_modal_render_can_get_team_info_for_locked_slot(self):
        """模拟前端 modal renderModalTeam 的输入:
        m.home.name = '1A' → 解析出 team_id='1' → 查 allTeams 拿到 code_iso/name_zh."""
        result = self._real_qualification_data("A")
        # 模拟 allTeams dict (后端 /api/teams 返回的)
        all_teams = {
            "1": {"name": "Mexico", "name_zh": "墨西哥", "code_iso": "mx", "code_fifa": "MEX"},
            "2": {"name": "South Korea", "name_zh": "韩国", "code_iso": "kr", "code_fifa": "KOR"},
        }
        # 前端 resolveBracketPlaceholder('1A') 应该返回:
        #   standings[0].team_id = '1' → allTeams['1'] → {name_zh: '墨西哥', code_iso: 'mx', ...}
        slot_team_id = result["standings"][0]["team_id"]
        resolved = all_teams.get(slot_team_id)
        assert resolved is not None
        assert resolved["name_zh"] == "墨西哥"
        assert resolved["code_iso"] == "mx"
        assert resolved["name"] == "Mexico"
