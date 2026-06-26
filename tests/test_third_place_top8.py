"""Tests for Plan 042 — Best 3rd-place race Top 8 panel.

Verifies the rendered HTML:
- Contains all 12 third-placed teams
- Top 8 (rank 1-8) get row-advance class + status-advance
- Bottom 4 (rank 9-12) get row-eliminate class + status-eliminate
- A divider row separates top 8 from bottom 4
- Each row has a flag span, team name, group letter, and stats
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import json

import pytest

# Path to the frontend asset we'll smoke-test by parsing the rendered HTML.
# We don't need a real browser — we just exec the function with a mock
# `allQualification` and `allTeams` dict in a JSDOM-ish way.
#
# Since main.js uses ES6 + DOM, the cheapest accurate test is to evaluate
# the JS in a happy-EQE script context. We do that by spawning Node and
# stubbing document/window. See TestRenderTop8Panel.test_render_full_payload.

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = (PROJECT_ROOT / "src" / "static" / "js" / "main.js").read_text(encoding="utf-8")


class TestRenderTop8Panel:
    """Exec main.js's renderThirdPlaceTop8() under a JSDOM stub and assert
    the produced HTML structure. This is the most accurate way to test
    frontend rendering without bringing in a full browser harness.

    We pull just the function bodies (and helpers they reference) out of
    main.js, evaluate them in a Node sandbox with stubbed document /
    allTeams / allQualification globals, and inspect innerHTML.
    """

    @pytest.fixture
    def sandbox(self):
        """Return a callable `run(qualification, teams)` that executes the
        render code under a stubbed DOM and returns {body, updated}.
        """
        import subprocess
        import textwrap

        # Build a self-contained script: provide a minimal `document`
        # object that captures innerHTML writes, and stub the helper
        # functions main.js expects (escapeHtml, _numOrZero, BEIJING_OFFSET_MS).
        # Then evaluate just the new functions (and their dependencies).
        harness = textwrap.dedent(r"""
            // === Sandbox harness ===
            const BEIJING_OFFSET_MS = 8 * 60 * 60 * 1000;
            function escapeHtml(s) {
                if (s == null) return '';
                return String(s)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            }
            function _numOrZero(v) {
                if (v === null || v === undefined || v === '') return 0;
                const n = parseInt(v, 10);
                return isNaN(n) ? 0 : n;
            }

            // Capture innerHTML writes
            const _captured = {};
            const document = {
                getElementById(id) {
                    if (!_captured[id]) _captured[id] = { innerHTML: '', textContent: '' };
                    return _captured[id];
                },
            };

            // === Code under test (cut from main.js verbatim) ===
            __CODE__

            // === Test driver ===
            renderThirdPlaceTop8();
            (function () {
                const out = {
                    body: _captured['third-place-body'] ? _captured['third-place-body'].innerHTML : '',
                    updated: _captured['third-place-updated'] ? _captured['third-place-updated'].textContent : '',
                };
                process.stdout.write(JSON.stringify(out));
            })();
        """).strip()

        # Extract just the new functions from main.js.
        # We slice from "function _flagForTeam" to the end of "rowsForRanking".
        start = MAIN_JS.find("function _flagForTeam")
        assert start != -1, "could not locate _flagForTeam in main.js"
        # Find the closing brace of rowsForRanking (last function we added)
        end = MAIN_JS.find("function resolveBracketPlaceholder", start)
        assert end != -1, "could not locate end marker (resolveBracketPlaceholder)"
        code_block = MAIN_JS[start:end].strip()

        def _run(all_qualification, all_teams):
            script = harness.replace("__CODE__", code_block)
            node_input = (
                "global.allQualification = "
                + json.dumps(all_qualification)
                + ";\n"
                + "global.allTeams = "
                + json.dumps(all_teams)
                + ";\n"
                + script
            )
            result = subprocess.run(
                ["node", "-e", node_input],
                capture_output=True, text=True, timeout=15,
            )
            assert result.returncode == 0, (
                f"node exit {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )
            return json.loads(result.stdout)

        return _run

    def _sample_rankings(self) -> list[dict]:
        return [
            {"team_id": "23", "group": "F", "pts": 4, "gd": 0, "gf": 7, "ga": 7, "w": 1, "d": 1, "l": 1, "mp": 3},
            {"team_id": "20", "group": "E", "pts": 4, "gd": 0, "gf": 2, "ga": 2, "w": 1, "d": 1, "l": 1, "mp": 3},
            {"team_id": "6",  "group": "B", "pts": 4, "gd": -1, "gf": 5, "ga": 6, "w": 1, "d": 1, "l": 1, "mp": 3},
            {"team_id": "46", "group": "L", "pts": 3, "gd": -1, "gf": 3, "ga": 4, "w": 1, "d": 0, "l": 1, "mp": 2},
            {"team_id": "3",  "group": "A", "pts": 3, "gd": -1, "gf": 2, "ga": 3, "w": 1, "d": 0, "l": 2, "mp": 3},
            {"team_id": "14", "group": "D", "pts": 3, "gd": -2, "gf": 2, "ga": 4, "w": 1, "d": 0, "l": 1, "mp": 2},
            {"team_id": "38", "group": "J", "pts": 3, "gd": -2, "gf": 2, "ga": 4, "w": 1, "d": 0, "l": 1, "mp": 2},
            {"team_id": "12", "group": "C", "pts": 3, "gd": -3, "gf": 1, "ga": 4, "w": 1, "d": 0, "l": 2, "mp": 3},
            {"team_id": "27", "group": "H", "pts": 2, "gd": 0, "gf": 2, "ga": 2, "w": 0, "d": 2, "l": 0, "mp": 2},
            {"team_id": "11", "group": "G", "pts": 2, "gd": 0, "gf": 1, "ga": 1, "w": 0, "d": 2, "l": 0, "mp": 2},
            {"team_id": "44", "group": "K", "pts": 1, "gd": -1, "gf": 1, "ga": 2, "w": 0, "d": 1, "l": 1, "mp": 2},
            {"team_id": "30", "group": "I", "pts": 0, "gd": -3, "gf": 3, "ga": 6, "w": 0, "d": 0, "l": 2, "mp": 2},
        ]

    def _sample_teams(self) -> dict:
        return {
            "23": {"name": "Sweden",              "name_zh": "瑞典",     "code_iso": "se"},
            "20": {"name": "Ecuador",             "name_zh": "厄瓜多尔", "code_iso": "ec"},
            "6":  {"name": "Bosnia and Herzegovina", "name_zh": "波黑", "code_iso": "ba"},
            "46": {"name": "Croatia",             "name_zh": "克罗地亚", "code_iso": "hr"},
            "3":  {"name": "South Korea",         "name_zh": "韩国",     "code_iso": "kr"},
            "14": {"name": "Paraguay",            "name_zh": "巴拉圭",   "code_iso": "py"},
            "38": {"name": "Algeria",             "name_zh": "阿尔及利亚","code_iso": "dz"},
            "12": {"name": "Scotland",            "name_zh": "苏格兰",   "code_iso": "gb-sct"},
            "27": {"name": "Cape Verde",          "name_zh": "佛得角",   "code_iso": "cv"},
            "11": {"name": "Belgium",             "name_zh": "比利时",   "code_iso": "be"},
            "44": {"name": "DR Congo",            "name_zh": "民主刚果", "code_iso": "cd"},
            "30": {"name": "Senegal",             "name_zh": "塞内加尔", "code_iso": "sn"},
        }

    def test_render_full_payload(self, sandbox):
        result = sandbox(
            all_qualification={
                "groups": {},
                "best_3rd_race": {"rankings": self._sample_rankings()},
                "generated_at": "2026-06-26T01:11:00+00:00",
            },
            all_teams=self._sample_teams(),
        )
        body = result["body"]
        assert body, "expected non-empty body HTML"
        # All 12 teams should appear (look up by name_zh since ids are not in HTML)
        for t in self._sample_rankings():
            zh = self._sample_teams()[t["team_id"]]["name_zh"]
            assert zh in body, f"team {t['team_id']} ({zh}) missing from rendered HTML"
        # 8 advance + 4 eliminate rows
        assert body.count("row-advance") == 8, "expected 8 advance rows"
        assert body.count("row-eliminate") == 4, "expected 4 eliminate rows"
        # 8 advance badges
        assert body.count("status-advance") == 8
        assert body.count("status-eliminate") == 4
        # Divider row present
        assert "row-divider" in body
        # Group letters present
        for letter in "ABCDEFGHIJKL":
            if any(t["group"] == letter for t in self._sample_rankings()):
                assert f">{letter}<" in body, f"group {letter} missing"
        # Flags present (one per team)
        assert body.count('class="fi fi-') == 12
        # Status update text rendered with Beijing time
        assert "北京时间" in result["updated"]
        assert "2026-06-26" in result["updated"]

    def test_render_empty_rankings(self, sandbox):
        result = sandbox(
            all_qualification={
                "groups": {},
                "best_3rd_race": {"rankings": []},
                "generated_at": "2026-06-26T01:11:00+00:00",
            },
            all_teams={},
        )
        assert "暂无第 3 名数据" in result["body"]

    def test_render_null_qualification(self, sandbox):
        result = sandbox(
            all_qualification=None,
            all_teams={},
        )
        assert "暂无第 3 名数据" in result["body"]
        assert result["updated"] == "—"

    def test_gd_sign_formatting(self, sandbox):
        """GD +1 should render as '+1', GD 0 as '0', GD -1 as '-1'."""
        result = sandbox(
            all_qualification={
                "groups": {},
                "best_3rd_race": {
                    "rankings": [
                        {"team_id": "A", "group": "A", "pts": 4, "gd": 2,  "gf": 3, "ga": 1, "w": 1, "d": 1, "l": 0, "mp": 2},
                        {"team_id": "B", "group": "B", "pts": 3, "gd": 0,  "gf": 1, "ga": 1, "w": 0, "d": 1, "l": 0, "mp": 1},
                        {"team_id": "C", "group": "C", "pts": 1, "gd": -1, "gf": 0, "ga": 1, "w": 0, "d": 0, "l": 1, "mp": 1},
                    ]
                },
                "generated_at": None,
            },
            all_teams={
                "A": {"name": "Alpha", "name_zh": "甲", "code_iso": "aa"},
                "B": {"name": "Beta",  "name_zh": "乙", "code_iso": "bb"},
                "C": {"name": "Gamma", "name_zh": "丙", "code_iso": "cc"},
            },
        )
        body = result["body"]
        assert ">+2<" in body, f"expected +2 in GD, got body: {body[:500]}"
        # The zero GD cell — find a cell containing class="col-gd">0<
        assert 'col-gd">0<' in body
        assert ">−1<" in body or ">-1<" in body
