"""Member 2 (Wijdan): number 2 in cycle 1 and number 9 in cycle 2."""

from digit_relay.relay_base import RelayMemberNode, run


class Member4(RelayMemberNode):
    MEMBER_ID = 2
    PEN_COLOR = (0, 255, 255)  # cyan

    def draw_cycle1(self):
        # Number 2: 
        self.stroke([(0.0, 2.0), (1.0, 2.0), (1.0, 0.0), (0.0, 0.0)])
        self.stroke([(0.0, 1.0), (1.0, 1.0)])

    def draw_cycle2(self):
        # Number 9: 
        self.draw_digit(9)


def main(args=None):
    run(Member4, args)


if __name__ == '__main__':
    main()
