"""Member 4 (Chelsea): number 4 in cycle 1 and number 11 in cycle 2."""

from digit_relay.relay_base import RelayMemberNode, run


class Member4(RelayMemberNode):
    MEMBER_ID = 4
    PEN_COLOR = (255, 255, 0)  # yellow

    def draw_cycle1(self):
        # Number 4: left stroke and crossbar, then the right vertical stroke.
        self.stroke([(0.0, 2.0), (0.0, 1.0), (1.0, 1.0)])
        self.stroke([(1.0, 2.0), (1.0, 0.0)])

    def draw_cycle2(self):
        # Number 11: draw one 1 in each digit position.
        self.draw_digit(1, digit=0)
        self.draw_digit(1, digit=1)


def main(args=None):
    run(Member4, args)


if __name__ == '__main__':
    main()
