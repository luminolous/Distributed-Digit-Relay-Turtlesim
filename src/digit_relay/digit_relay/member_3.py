"""Member 3 (Sultan): number 3 in cycle 1 and number 10 in cycle 2."""

from digit_relay.relay_base import RelayMemberNode, run


class Member3(RelayMemberNode):
    MEMBER_ID = 3
    PEN_COLOR = (0, 255, 0)  # green

    def draw_cycle1(self):
        # Number 3: top bar, right side down, bottom bar, then the middle bar.
        self.stroke([(0.0, 2.0), (1.0, 2.0), (1.0, 0.0), (0.0, 0.0)])
        self.stroke([(0.0, 1.0), (1.0, 1.0)])

    def draw_cycle2(self):
        # Number 10: 1 in the left digit position, 0 in the right one.
        self.draw_digit(1, digit=0)
        self.draw_digit(0, digit=1)


def main(args=None):
    run(Member3, args)


if __name__ == '__main__':
    main()
