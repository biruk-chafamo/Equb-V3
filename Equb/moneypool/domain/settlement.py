import random
from decimal import Decimal
from typing import Callable, Optional, Sequence, TypeVar

Member = TypeVar("Member")


def compute_award(pot_amount: Decimal, max_members: int, bid_amount, not_received_count: int) -> Decimal:
    """
    The amount credited to a round's winner: the full pot, minus a
    discount proportional to the bid and to how many not-yet-received
    members (not_received_count) are around to benefit from it.
    """
    contributions_from_non_recieved = pot_amount * Decimal(not_received_count) / Decimal(max_members)
    winners_contribution = contributions_from_non_recieved * Decimal(bid_amount)
    return pot_amount - winners_contribution


def compute_deduction(
    pot_amount: Decimal,
    max_members: int,
    bid_amount,
    in_not_received: bool,
) -> Decimal:
    if in_not_received:
        return (pot_amount / Decimal(max_members)) * (Decimal(1) - Decimal(bid_amount))
    else:
        return pot_amount / Decimal(max_members)


