from decimal import Decimal

from hypothesis import given, settings, strategies as st

from .settlement import compute_award, compute_deduction


_PRECISION_EPSILON = Decimal("1E-20")
_amounts = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("1000000.00"), places=2)
_max_members = st.integers(min_value=2, max_value=20)
_bids = st.one_of(
    st.just(0),
    st.decimals(min_value=Decimal("0.001"), max_value=Decimal("1.000"), places=3),
)


@given(pot=_amounts, max_members=_max_members, bid=_bids, data=st.data())
@settings(max_examples=300)
def test_conservation_is_exact_for_every_not_received_count(pot, max_members, bid, data):
    """
    For ANY split of the (max_members - 1) non-winner members into `k`
    "not received" and the rest "already received" (paying their flat share), the
    sum of everyone's deduction equals award - pot/max_members -- exactly, for
    every k from 0 (the final round) to max_members - 1 (round 1).
    """
    not_received_count = data.draw(st.integers(min_value=0, max_value=max_members - 1))
    already_received_count = (max_members - 1) - not_received_count

    award = compute_award(pot, max_members, bid, not_received_count)
    non_deductible_award = pot / max_members
    deducted_award = award - non_deductible_award

    total_collected = Decimal("0")
    if not_received_count > 0:
        per_not_received = compute_deduction(pot, max_members, bid, in_not_received=True)
        total_collected += per_not_received * not_received_count
    if already_received_count > 0:
        per_already_received = compute_deduction(pot, max_members, bid, in_not_received=False)
        total_collected += per_already_received * already_received_count

    assert abs(total_collected - deducted_award) < _PRECISION_EPSILON


@given(pot=_amounts, max_members=_max_members, bid=_bids)
@settings(max_examples=300)
def test_final_round_does_not_overcollect(pot, max_members, bid):
    """
    at not_received_count=0 (final round), every non-winner is an already-received flat payer.
    Confirms the total they pay now matches the award, for any bid
    """
    already_received_count = max_members - 1
    per_already_received = compute_deduction(pot, max_members, bid, in_not_received=False)
    total_collected = per_already_received * already_received_count

    award = compute_award(pot, max_members, bid, not_received_count=0)
    deducted_award = award - (pot / max_members)

    assert abs(total_collected - deducted_award) < _PRECISION_EPSILON
    # and bid has no effect at all at k=0, meaning award is always the full pot
    assert award == pot


@given(pot=_amounts, max_members=_max_members, bid=_bids, not_received_count=st.integers(min_value=0, max_value=19))
@settings(max_examples=300)
def test_compute_award_is_deterministic(pot, max_members, bid, not_received_count):
    results = {compute_award(pot, max_members, bid, not_received_count) for _ in range(5)}
    assert len(results) == 1


