"""Member 7 node: number 7 (cycle 1) and 14 (cycle 2).

The base class handles the turn token, slot positioning, pen, and termination.
Stroke coordinates use the local glyph box: x 0..1, y 0..2.
"""

from digit_relay.relay_base import RelayMemberNode, run


class Member7(RelayMemberNode):
    MEMBER_ID = 7
    PEN_COLOR = (255, 165, 0)  # orange

    def draw_cycle1(self):
        # Number 7: top bar followed by the diagonal downstroke.
        self.stroke([(0.0, 2.0), (1.0, 2.0), (0.4, 0.0)])

    def draw_cycle2(self):
        # Number 14: place each digit in its own glyph box within slot 7.
        self.draw_digit(1, digit=0)
        self.draw_digit(4, digit=1)


def main(args=None):
    run(Member7, args)


if __name__ == '__main__':
    main()
