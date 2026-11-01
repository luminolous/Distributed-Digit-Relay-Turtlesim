"""Member 5 (Fa'iz): draw 5 in cycle 1 and 12 in cycle 2."""

from digit_relay.relay_base import RelayMemberNode, run


class Member5(RelayMemberNode):
    MEMBER_ID = 5
    PEN_COLOR = (160, 32, 240)  # purple; confirm it is unique with member 6

    def draw_cycle1(self):
        self.draw_digit(5)

    def draw_cycle2(self):
        # Draw 12 as a 1 in the first digit position and a 2 in the second.
        self.draw_digit(1, digit=0)
        self.draw_digit(2, digit=1)


def main(args=None):
    run(Member5, args)


if __name__ == '__main__':
    main()
