"""Canvas layout: the single source of truth for slot positions.

The turtlesim canvas spans 0.0 .. 11.0. Every slot fits a 2-digit number:
two glyph boxes (1.0 x 2.0) side by side, separated by DIGIT_GAP.
"""

NUM_MEMBERS = 7
NUM_CYCLES = 2
LAST_NUMBER = NUM_MEMBERS * NUM_CYCLES

# Local glyph box size for one digit, (0, 0) = bottom-left.
GLYPH_WIDTH = 1.0
GLYPH_HEIGHT = 2.0
DIGIT_GAP = 0.2
SLOT_WIDTH = 2 * GLYPH_WIDTH + DIGIT_GAP  # 2.2

# Safe canvas bounds (0.5 margin from the walls).
CANVAS_MIN = 0.5
CANVAS_MAX = 10.5

# Bottom-left origin of each member's slot, in turtlesim world coordinates.
# Top row: members 1-4, bottom row: members 5-7.
SLOT_ORIGIN = {
    1: (0.60, 6.5),
    2: (3.10, 6.5),
    3: (5.60, 6.5),
    4: (8.10, 6.5),
    5: (1.85, 2.0),
    6: (4.35, 2.0),
    7: (6.85, 2.0),
}

# Where the turtle parks between turns: the gap between rows, not covering any number.
PARK_POSE = (5.544, 5.25, 0.0)


def glyph_to_world(member_id, n_digits, digit, lx, ly, scale):
    """Convert local glyph point (lx, ly) of digit index `digit` into world coordinates.

    Slot content is centered: a 1-digit number sits in the middle of the 2-digit-wide slot.
    """
    content_w = (n_digits * GLYPH_WIDTH + (n_digits - 1) * DIGIT_GAP) * scale
    content_h = GLYPH_HEIGHT * scale
    ox, oy = SLOT_ORIGIN[member_id]
    left = ox + (SLOT_WIDTH - content_w) / 2
    bottom = oy + (GLYPH_HEIGHT - content_h) / 2
    x = left + scale * (digit * (GLYPH_WIDTH + DIGIT_GAP) + lx)
    y = bottom + scale * ly
    return x, y


def cycle_of(number):
    """Cycle of a number: 1..7 -> 1, 8..14 -> 2."""
    return (number - 1) // NUM_MEMBERS + 1


def next_member(member_id):
    """Next member, wrapping around: 7 -> 1."""
    return member_id % NUM_MEMBERS + 1


def number_for(member_id, cycle):
    """The number a member draws in a given cycle."""
    return (cycle - 1) * NUM_MEMBERS + member_id
