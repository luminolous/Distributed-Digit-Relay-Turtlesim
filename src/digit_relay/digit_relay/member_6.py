"""Member 6 node: number 6 (cycle 1) and 13 (cycle 2)."""

from digit_relay.relay_base import RelayMemberNode, run


class Member6(RelayMemberNode):
    MEMBER_ID = 6
    PEN_COLOR = (255, 0, 255)  # magenta

    def draw_cycle1(self):
        # Number 6
        self.draw_digit(6)

    def draw_cycle2(self):
        # Number 13: one digit in each glyph box within slot 6.
        self.draw_digit(1, digit=0)
        self.draw_digit(3, digit=1)


def main(args=None):
    run(Member6, args)


if __name__ == '__main__':
    main()
