"""ROS-free layout checks: numbers 1..14 stay inside the canvas and never overlap."""

import itertools

import pytest

from digit_relay import glyphs, layout

# Must match RelayMemberNode.SCALE.
SCALE = 0.8
# Minimum spacing between numbers in different slots, so "10" and "11" do not read as "1011".
MIN_SLOT_SPACING = 0.5


def number_bbox(member_id, number):
    """Bounding box (xmin, ymin, xmax, ymax) of a number drawn with the built-in glyphs."""
    digits = str(number)
    xs, ys = [], []
    for i, ch in enumerate(digits):
        for stroke in glyphs.DIGIT[int(ch)]:
            for lx, ly in stroke:
                x, y = layout.glyph_to_world(member_id, len(digits), i, lx, ly, SCALE)
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def all_boxes(cycle):
    return {
        m: number_bbox(m, layout.number_for(m, cycle))
        for m in range(1, layout.NUM_MEMBERS + 1)
    }


@pytest.mark.parametrize('cycle', range(1, layout.NUM_CYCLES + 1))
def test_inside_canvas(cycle):
    for member_id, (x0, y0, x1, y1) in all_boxes(cycle).items():
        assert layout.CANVAS_MIN <= x0 and x1 <= layout.CANVAS_MAX, member_id
        assert layout.CANVAS_MIN <= y0 and y1 <= layout.CANVAS_MAX, member_id


@pytest.mark.parametrize('cycle', range(1, layout.NUM_CYCLES + 1))
def test_no_overlap(cycle):
    boxes = all_boxes(cycle)
    for a, b in itertools.combinations(boxes, 2):
        ax0, ay0, ax1, ay1 = boxes[a]
        bx0, by0, bx1, by1 = boxes[b]
        gap_x = max(bx0 - ax1, ax0 - bx1)
        gap_y = max(by0 - ay1, ay0 - by1)
        assert max(gap_x, gap_y) >= MIN_SLOT_SPACING, (a, b)


def test_park_pose_clear_of_slots():
    px, py, _ = layout.PARK_POSE
    for cycle in range(1, layout.NUM_CYCLES + 1):
        for x0, y0, x1, y1 in all_boxes(cycle).values():
            assert not (x0 - 0.5 <= px <= x1 + 0.5 and y0 - 0.5 <= py <= y1 + 0.5)


def test_token_math():
    assert [layout.cycle_of(n) for n in (1, 7, 8, 14)] == [1, 1, 2, 2]
    assert layout.next_member(7) == 1
    assert layout.number_for(3, 2) == 10
    assert layout.LAST_NUMBER == 14
