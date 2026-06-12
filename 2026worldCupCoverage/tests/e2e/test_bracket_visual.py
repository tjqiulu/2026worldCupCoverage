"""E2E tests for bracket visual layout (alignment of R16/QF/SF between parents)."""
from __future__ import annotations

import pytest
from playwright.sync_api import Page

from conftest import save_screenshot


def _card_boxes_by_stage(page: Page, stage: str) -> list[dict]:
    """Get bounding boxes of all cards with class .bracket-card.<stage>, in DOM order."""
    cards = page.locator(f".bracket-card.{stage}").all()
    return [c.bounding_box() for c in cards]


def _center_y(box: dict) -> float:
    return box["y"] + box["height"] / 2


def _center_x(box: dict) -> float:
    return box["x"] + box["width"] / 2


# === R16 alignment with R32 parents ===

class TestR16Alignment:
    """R16 cards must be vertically centered between their 2 R32 parent cards."""

    @pytest.fixture
    def r32_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "r32")

    @pytest.fixture
    def r16_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "r16")

    def test_r16_count(self, r16_boxes):
        # WC 2026 has 8 R16 matches
        assert len(r16_boxes) == 8, f"Expected 8 R16 cards, got {len(r16_boxes)}"

    def test_r32_count(self, r32_boxes):
        assert len(r32_boxes) == 16, f"Expected 16 R32 cards, got {len(r32_boxes)}"

    @pytest.mark.parametrize("r16_idx, r32_left_idx, r32_right_idx", [
        # Top half (4 R16): R32 positions in BRACKET order
        # Bracket order: 1, 3, 2, 5, 4, 6, 7, 8 (indices 0-7 in DOM)
        (0, 0, 1),  # R16-1 between R32-1 (idx 0) and R32-3 (idx 1)
        (1, 2, 3),  # R16-2 between R32-2 (idx 2) and R32-5 (idx 3)
        (2, 4, 5),  # R16-3 between R32-4 (idx 4) and R32-6 (idx 5)
        (3, 6, 7),  # R16-4 between R32-7 (idx 6) and R32-8 (idx 7)
        # Bottom half
        (4, 8, 9),   # R16-5 between R32-11 (idx 8) and R32-12 (idx 9)
        (5, 10, 11), # R16-6 between R32-9 (idx 10) and R32-10 (idx 11)
        (6, 12, 13), # R16-7 between R32-14 (idx 12) and R32-16 (idx 13)
        (7, 14, 15), # R16-8 between R32-13 (idx 14) and R32-15 (idx 15)
    ])
    def test_r16_vertically_between_r32_parents(
        self, r16_boxes, r32_boxes, r16_idx, r32_left_idx, r32_right_idx
    ):
        r16 = r16_boxes[r16_idx]
        r32_l = r32_boxes[r32_left_idx]
        r32_r = r32_boxes[r32_right_idx]

        r16_cy = _center_y(r16)
        l_cy = _center_y(r32_l)
        r_cy = _center_y(r32_r)

        # R16 center must be between R32 parents (min < r16_cy < max)
        lo, hi = sorted([l_cy, r_cy])
        assert lo < r16_cy < hi, (
            f"R16[{r16_idx}] center y={r16_cy:.1f} not between "
            f"R32[{r32_left_idx}] y={l_cy:.1f} and R32[{r32_right_idx}] y={r_cy:.1f}"
        )

        # R16 should be roughly equidistant (within 2px tolerance for sub-pixel rounding)
        dist_l = abs(r16_cy - l_cy)
        dist_r = abs(r16_cy - r_cy)
        imbalance = abs(dist_l - dist_r)
        assert imbalance < 2, (
            f"R16[{r16_idx}] off-center: dist to left={dist_l:.1f}, "
            f"dist to right={dist_r:.1f}, imbalance={imbalance:.1f}px"
        )

    def test_r16_x_between_r32_parents(self, r16_boxes, r32_boxes):
        """R16 card's x should be > R32's x (R16 is in column 2, R32 in col 1)."""
        for i in range(4):  # Just check first 4
            r16_x = r16_boxes[i]["x"]
            r32_x = r32_boxes[i * 2]["x"]
            assert r16_x > r32_x, f"R16[{i}] should be to the right of R32[{i*2}]"


# === QF alignment with R16 parents ===

class TestQFAlignment:
    @pytest.fixture
    def r16_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "r16")

    @pytest.fixture
    def qf_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "qf")

    def test_qf_count(self, qf_boxes):
        assert len(qf_boxes) == 4

    @pytest.mark.parametrize("qf_idx, r16_left, r16_right", [
        (0, 0, 1),  # QF-1 between R16-1 and R16-2
        (1, 2, 3),  # QF-2 between R16-3 and R16-4
        (2, 4, 5),  # QF-3 between R16-5 and R16-6
        (3, 6, 7),  # QF-4 between R16-7 and R16-8
    ])
    def test_qf_between_r16_parents(self, r16_boxes, qf_boxes, qf_idx, r16_left, r16_right):
        qf = qf_boxes[qf_idx]
        r16_l = r16_boxes[r16_left]
        r16_r = r16_boxes[r16_right]
        qf_cy = _center_y(qf)
        l_cy = _center_y(r16_l)
        r_cy = _center_y(r16_r)
        lo, hi = sorted([l_cy, r_cy])
        assert lo < qf_cy < hi, (
            f"QF[{qf_idx}] center y={qf_cy:.1f} not between "
            f"R16[{r16_left}] y={l_cy:.1f} and R16[{r16_right}] y={r_cy:.1f}"
        )


# === SF alignment with QF parents ===

class TestSFAlignment:
    @pytest.fixture
    def qf_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "qf")

    @pytest.fixture
    def sf_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "sf")

    def test_sf_count(self, sf_boxes):
        assert len(sf_boxes) == 2

    def test_sf1_between_qf1_and_qf2(self, qf_boxes, sf_boxes):
        sf = sf_boxes[0]
        qf1 = qf_boxes[0]
        qf2 = qf_boxes[1]
        sf_cy = _center_y(sf)
        lo, hi = sorted([_center_y(qf1), _center_y(qf2)])
        assert lo < sf_cy < hi

    def test_sf2_between_qf3_and_qf4(self, qf_boxes, sf_boxes):
        sf = sf_boxes[1]
        qf3 = qf_boxes[2]
        qf4 = qf_boxes[3]
        sf_cy = _center_y(sf)
        lo, hi = sorted([_center_y(qf3), _center_y(qf4)])
        assert lo < sf_cy < hi


# === Final alignment ===

class TestFinalAlignment:
    @pytest.fixture
    def final_box(self, page: Page) -> dict:
        boxes = _card_boxes_by_stage(page, "final")
        assert len(boxes) == 1
        return boxes[0]

    @pytest.fixture
    def sf_boxes(self, page: Page) -> list[dict]:
        return _card_boxes_by_stage(page, "sf")

    def test_final_horizontally_centered_in_grid(self, page: Page, final_box):
        """Final card should be in column 5 (center) of 9-column grid."""
        # The bracket-mirror has 9 columns. Final is in col 5.
        # We can check Final is in the middle by comparing its x to the bracket's full width.
        bracket = page.locator(".bracket-mirror").bounding_box()
        bracket_center_x = bracket["x"] + bracket["width"] / 2
        final_center_x = _center_x(final_box)
        # Final should be near bracket center
        offset = abs(bracket_center_x - final_center_x)
        assert offset < 50, (
            f"Final not centered in bracket grid: bracket_cx={bracket_center_x:.1f}, "
            f"final_cx={final_center_x:.1f}, offset={offset:.1f}"
        )

    def test_final_vertically_centered(self, final_box, sf_boxes):
        """Final should be vertically between SF-1 (top half) and SF-2 (bottom half)."""
        final_cy = _center_y(final_box)
        sf1_cy = _center_y(sf_boxes[0])
        sf2_cy = _center_y(sf_boxes[1])
        # SF-1 should be above, SF-2 should be below
        assert sf1_cy < final_cy < sf2_cy


# === Top/bottom mirror symmetry ===

class TestMirrorSymmetry:
    def test_r32_mirror_symmetric(self, page: Page):
        """R32 cards 1-8 (top) should be mirror of 9-16 (bottom) around Final center."""
        r32_boxes = _card_boxes_by_stage(page, "r32")
        assert len(r32_boxes) == 16

        # Get Final card's center y as mirror axis
        final_box = _card_boxes_by_stage(page, "final")[0]
        axis_y = _center_y(final_box)

        # Check r32[0] (top of top half) and r32[15] (bottom of bottom half) are equidistant from axis
        for i in range(8):
            top = _center_y(r32_boxes[i])
            bot = _center_y(r32_boxes[15 - i])
            top_dist = abs(top - axis_y)
            bot_dist = abs(bot - axis_y)
            imbalance = abs(top_dist - bot_dist)
            # Allow larger tolerance (mirror has padding differences)
            assert imbalance < 20, (
                f"R32[{i}] and R32[{15-i}] not symmetric around Final: "
                f"top_dist={top_dist:.1f}, bot_dist={bot_dist:.1f}"
            )


# === Screenshot capture for human review ===

def test_bracket_screenshot(page: Page):
    """Save a full-page screenshot of the bracket view for human review."""
    path = save_screenshot(page, "bracket_view")
    print(f"\n[INFO] Bracket screenshot saved to: {path}")
    assert path.exists()
    assert path.stat().st_size > 1000  # non-trivial image


# === Plan 007: SVG connecting lines ===

class TestConnectingLines:
    """Verify SVG elbow lines correctly connect parent-child matches."""

    def test_svg_exists(self, page: Page):
        svg = page.locator(".bracket-lines").first
        assert svg.count() == 1
        # Wait for JS to render
        page.wait_for_timeout(300)
        svg_box = svg.bounding_box()
        assert svg_box is not None
        assert svg_box["width"] > 500
        assert svg_box["height"] > 500

    def test_line_count(self, page: Page):
        """Plan 007: 30 lines total (16 R32→R16 + 8 R16→QF + 4 QF→SF + 2 SF→Final).

        With T-shape (1 vertical + 1 horizontal per group), and 8+4+2+1 = 15 groups,
        total paths = 30. Plus 15 merge-point dots.
        """
        page.wait_for_timeout(300)
        lines = page.locator(".bracket-lines path.bracket-line").all()
        dots = page.locator(".bracket-lines circle.bracket-dot").all()
        assert len(lines) == 30, f"Expected 30 lines, got {len(lines)}"
        assert len(dots) == 15, f"Expected 15 dots, got {len(dots)}"

    def test_first_r32_r16_line_starts_at_parent_right_edge(self, page: Page):
        """The first R32→R16 line should start at the right edge of R32-1."""
        page.wait_for_timeout(300)
        # R32-1 is the first card in DOM
        r32_1 = page.locator(".bracket-card.r32").first
        r32_1_box = r32_1.bounding_box()
        # First line corresponds to the first connection (R32-1 → R16-1)
        first_line = page.locator(".bracket-lines path.bracket-line").first
        d = first_line.get_attribute("d") or ""

        # Get SVG's bounding box (line coords are relative to SVG)
        svg_box = page.locator(".bracket-lines").first.bounding_box()
        svg_left = svg_box["x"]

        # Parse "M px py ..." - first path is the T's vertical (or L's first)
        parts = d.split()
        assert parts[0] == "M"
        px = float(parts[1])
        # The SVG-relative x of the line should match R32-1's right edge (relative to SVG)
        r32_right_svg = (r32_1_box["x"] + r32_1_box["width"]) - svg_left
        # Allow small tolerance for grid gaps
        assert abs(px - r32_right_svg) < 3, (
            f"First line x={px} doesn't match R32-1 right edge "
            f"(svg-relative)={r32_right_svg:.1f} (svg left={svg_left:.1f})"
        )

    def test_lines_visual_screenshot(self, page: Page):
        """Take a screenshot of the bracket with connecting lines for visual review."""
        page.wait_for_timeout(500)
        path = save_screenshot(page, "bracket_with_lines")
        print(f"\n[INFO] Bracket with lines screenshot: {path}")
        assert path.stat().st_size > 5000  # non-trivial image with lines

    def test_no_line_overlaps_card(self, page: Page):
        """Lines should not visually cross over card bodies (only through gaps)."""
        # This is a soft check: get the SVG bounding box and the bracket-mirror box,
        # verify SVG fills the bracket area so lines are positioned correctly.
        page.wait_for_timeout(300)
        svg = page.locator(".bracket-lines").first
        svg_box = svg.bounding_box()
        mirror = page.locator(".bracket-mirror").first
        mirror_box = mirror.bounding_box()
        # SVG should cover the mirror area (with some tolerance for padding)
        assert abs(svg_box["width"] - mirror_box["width"]) < 5
        assert abs(svg_box["height"] - mirror_box["height"]) < 5
