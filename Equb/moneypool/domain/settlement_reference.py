from fractions import Fraction
from typing import Sequence


def share(pot_amount, max_members) -> Fraction:
    return Fraction(pot_amount) / Fraction(max_members)


def award(pot_amount, max_members, bid_amount, not_received_count) -> Fraction:
    return share(pot_amount, max_members) * (
        Fraction(max_members) - Fraction(bid_amount) * Fraction(not_received_count)
    )


def deduction(pot_amount, max_members, bid_amount, in_not_received) -> Fraction:
    s = share(pot_amount, max_members)
    if in_not_received:
        return s * (Fraction(1) - Fraction(bid_amount))
    else:
        return s


def member_net(pot_amount, max_members, bids: Sequence, win_round: int) -> Fraction:
    """`bids[r - 1]` is the winning bid of round r; `win_round` is 1-based."""
    s = share(pot_amount, max_members)
    collected_while_waiting = sum(
        (Fraction(bids[r - 1]) for r in range(1, win_round)), Fraction(0)
    )
    paid_to_win_early = Fraction(bids[win_round - 1]) * Fraction(max_members - win_round)
    return s * (collected_while_waiting - paid_to_win_early)
