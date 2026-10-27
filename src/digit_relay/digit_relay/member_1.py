"""Member 1 node: number 1 (cycle 1) and 8 (cycle 2).

This file is also the reference template for the other members. Stroke coordinates
use the local glyph box: x 0..1, y 0..2, (0, 0) = bottom-left. The base class handles
the token, pen, moving between slots, and /clear.
"""

from digit_relay.relay_base import RelayMemberNode, run


class Member1(RelayMemberNode):
    MEMBER_ID = 1
    PEN_COLOR = (255, 0, 0)  # red

    def draw_cycle1(self):
        # Number 1: manual way, strokes defined by hand.
        self.stroke([(0.2, 1.6), (0.5, 2.0), (0.5, 0.0)])  # top hook + stem
        self.stroke([(0.2, 0.0), (0.8, 0.0)])              # base

    def draw_cycle2(self):
        # Number 8: quick way, use the built-in glyph from glyphs.DIGIT.
        self.draw_digit(8)


def main(args=None):
    run(Member1, args)


if __name__ == '__main__':
    main()
