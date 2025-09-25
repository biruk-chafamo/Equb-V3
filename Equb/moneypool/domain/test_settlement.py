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


def test_compute_deduction_at_max_bid_not_received_member():
    deduction = compute_deduction(Decimal("100.00"), 2, Decimal("1.000"), in_not_received=True)
    assert deduction == Decimal("0.00")


def test_compute_deduction_rounding_remainder_case():
    # amount=100, max_members=3, no bid means deduction is 100/3
    deduction = compute_deduction(Decimal("100.00"), 3, 0, in_not_received=True)
    expected = Decimal("100.00") / 3
    assert deduction == expected
    assert deduction != deduction.quantize(Decimal("0.01"))


def test_compute_deduction_mid_bid_three_member_scenario_exact_conservation():
    """
    3-member equb, mid-round bid: amount=90,
    max_members=3, bid=0.500, 1 winner + 2 not-yet-received members (k=2).
    """
    amount = Decimal("90.00")
    max_members = 3
    bid = Decimal("0.500")
    not_received_count = 2

    award = compute_award(amount, max_members, bid, not_received_count)
    deduction_each_loser = compute_deduction(amount, max_members, bid, in_not_received=True)

    # award = 90 - 90*(2/3)*0.5 = 90 - 30 = 60
    assert award == Decimal("60.000")
    # each loser: (90/3)*(1-0.5) = 15
    assert deduction_each_loser == Decimal("15.000")
    # both losers' deductions sum to exactly the collected portion (award - flat share)
    assert deduction_each_loser * 2 == award - (amount / max_members)


