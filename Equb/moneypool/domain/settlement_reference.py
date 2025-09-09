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


