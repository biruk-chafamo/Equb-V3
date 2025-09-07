from fractions import Fraction
from typing import Sequence


def share(pot_amount, max_members) -> Fraction:
    return Fraction(pot_amount) / Fraction(max_members)


