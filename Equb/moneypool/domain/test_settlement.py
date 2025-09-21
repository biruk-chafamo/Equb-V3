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


def test_compute_deduction_not_received_member_no_bid():
    deduction = compute_deduction(Decimal("100.00"), 2, 0, in_not_received=True)
    assert deduction == Decimal("50.00")


def test_compute_deduction_already_received_member_flat_share():
    deduction = compute_deduction(Decimal("100.00"), 2, 0, in_not_received=False)
    assert deduction == Decimal("50.00")


def test_pick_winner_prefers_highest_bidder():
    assert pick_winner("abeni", ["biruk", "dani"], rng=lambda seq: "should-not-be-called") == "abeni"


def test_pick_winner_falls_back_to_rng_when_no_bidder():
    assert pick_winner(None, ["biruk", "dani"], rng=lambda seq: seq[0]) == "biruk"


def test_is_higher_bid_true_when_no_current_highest():
    assert is_higher_bid(Decimal("0.100"), None) is True


def test_is_higher_bid_true_when_strictly_greater():
    assert is_higher_bid(Decimal("0.200"), Decimal("0.100")) is True


def test_compute_award_at_max_bid():
    award = compute_award(Decimal("100.00"), 2, Decimal("1.000"), not_received_count=1)
    assert award == Decimal("50.00")


