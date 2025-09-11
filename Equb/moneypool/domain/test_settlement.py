from decimal import Decimal

from .settlement import compute_award, compute_deduction, pick_winner, is_higher_bid


def test_compute_award_no_bid():
    # bid=0 means winner always gets the full pot, regardless of max_members
    # or not_received_count.
    award = compute_award(Decimal("100.00"), 2, 0, not_received_count=1)
    assert award == Decimal("100.00")


