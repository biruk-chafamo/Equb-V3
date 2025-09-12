from decimal import Decimal

from .settlement import compute_award, compute_deduction, pick_winner, is_higher_bid


def test_compute_award_no_bid():
    # bid=0 means winner always gets the full pot, regardless of max_members
    # or not_received_count.
    award = compute_award(Decimal("100.00"), 2, 0, not_received_count=1)
    assert award == Decimal("100.00")


def test_compute_award_with_bid():
    # pot=100, max_members=2, bid=0.9, k=1 (2-member equb: only one other
    # member, so not_received_count (k) is always 1):
    # award = 100 - 100*1/2*0.9 = 55
    award = compute_award(Decimal("100.00"), 2, Decimal("0.900"), not_received_count=1)
    assert award == Decimal("55.000")


