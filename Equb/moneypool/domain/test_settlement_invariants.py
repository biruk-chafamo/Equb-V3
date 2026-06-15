from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction

import pytest
from hypothesis import assume, given, settings, strategies as st

from . import settlement_reference as ref
from .settlement import compute_award, compute_deduction

POT_MIN = Decimal("1.00")
POT_MAX = Decimal("99999999999.99")
POT_PLACES = 2
MAX_MEMBERS_MIN = 2
MAX_MEMBERS_MAX = 20
BID_MIN = Decimal("0.001")
BID_MAX = Decimal("1.000")
BID_PLACES = 3

_pots = st.decimals(min_value=POT_MIN, max_value=POT_MAX, places=POT_PLACES)
_max_members = st.integers(min_value=MAX_MEMBERS_MIN, max_value=MAX_MEMBERS_MAX)
_bids = st.one_of(
    st.just(0),
    st.decimals(min_value=BID_MIN, max_value=BID_MAX, places=BID_PLACES),
)

_RELATIVE_TOLERANCE = Fraction(1, 10 ** 22)


def _tol(pot):
    return Fraction(pot) * _RELATIVE_TOLERANCE


def _close(actual, expected, pot):
    return abs(Fraction(actual) - Fraction(expected)) <= _tol(pot)


@st.composite
def _rounds(draw):
    pot = draw(_pots)
    max_members = draw(_max_members)
    bid = draw(_bids)
    not_received_count = draw(st.integers(min_value=0, max_value=max_members - 1))
    return pot, max_members, bid, not_received_count


# --- I1: totality ---------------------------------------------------------


@given(params=_rounds())
@settings(max_examples=300)
def test_settlement_is_total_over_the_legal_input_box(params):
    pot, max_members, bid, k = params
    award = compute_award(pot, max_members, bid, k)
    waiting = compute_deduction(pot, max_members, bid, in_not_received=True)
    received = compute_deduction(pot, max_members, bid, in_not_received=False)
    for value in (award, waiting, received):
        assert isinstance(value, Decimal)
        assert value.is_finite()


# --- I2: non-negativity ---------------------------------------------------


@given(params=_rounds())
@settings(max_examples=300)
def test_award_and_deductions_are_never_negative(params):
    pot, max_members, bid, k = params
    assert compute_award(pot, max_members, bid, k) >= 0
    assert compute_deduction(pot, max_members, bid, in_not_received=True) >= 0
    assert compute_deduction(pot, max_members, bid, in_not_received=False) >= 0


# --- I4: closed form ------------------------------------------------------


@given(params=_rounds())
@settings(max_examples=300)
def test_award_matches_the_closed_form(params):
    pot, max_members, bid, k = params
    assert _close(compute_award(pot, max_members, bid, k), ref.award(pot, max_members, bid, k), pot)


@pytest.mark.xfail(
    reason="F4: compute_award divides mid-expression; needs the divide-last form s*(N - b*k)",
    strict=False,
)
@given(params=_rounds())
@settings(max_examples=300)
def test_award_matches_the_closed_form_exactly(params):
    pot, max_members, bid, k = params
    closed_form = pot * (Decimal(max_members) - Decimal(bid) * Decimal(k)) / Decimal(max_members)
    assert compute_award(pot, max_members, bid, k) == closed_form


@given(params=_rounds())
@settings(max_examples=200)
def test_deductions_match_the_closed_form(params):
    pot, max_members, bid, k = params
    waiting = compute_deduction(pot, max_members, bid, in_not_received=True)
    received = compute_deduction(pot, max_members, bid, in_not_received=False)
    assert _close(waiting, ref.deduction(pot, max_members, bid, True), pot)
    assert _close(received, ref.deduction(pot, max_members, bid, False), pot)


# --- I5: homogeneity in the pot -------------------------------------------


@given(params=_rounds(), exponent=st.integers(min_value=-2, max_value=3))
@settings(max_examples=300)
def test_settlement_is_homogeneous_in_the_pot(params, exponent):
    pot, max_members, bid, k = params
    scale = Decimal(10) ** exponent
    scaled_pot = pot * scale
    assume(POT_MIN <= scaled_pot <= POT_MAX)

    assert compute_award(scaled_pot, max_members, bid, k) == scale * compute_award(pot, max_members, bid, k)
    assert compute_deduction(
        scaled_pot, max_members, bid, in_not_received=True
    ) == scale * compute_deduction(pot, max_members, bid, in_not_received=True)


# --- I6: round conservation, across the full pot range --------------------


@given(params=_rounds())
@settings(max_examples=400)
def test_round_conservation_holds_at_every_pot_magnitude(params):
    pot, max_members, bid, k = params
    already_received_count = (max_members - 1) - k

    waiting = compute_deduction(pot, max_members, bid, in_not_received=True)
    received = compute_deduction(pot, max_members, bid, in_not_received=False)
    collected = waiting * k + received * already_received_count

    expected = ref.award(pot, max_members, bid, k) - ref.share(pot, max_members)
    assert _close(collected, expected, pot)


# --- I7: discount duality -------------------------------------------------


@given(params=_rounds())
@settings(max_examples=300)
def test_the_winners_bidding_cost_equals_the_discount_granted(params):
    pot, max_members, bid, k = params
    s = ref.share(pot, max_members)

    winners_cost = Fraction(pot) - Fraction(compute_award(pot, max_members, bid, k))
    per_member_saving = s - Fraction(
        compute_deduction(pot, max_members, bid, in_not_received=True)
    )

    assert abs(winners_cost - Fraction(bid) * Fraction(k) * s) <= _tol(pot)
    assert abs(per_member_saving * Fraction(k) - winners_cost) <= _tol(pot)


# --- I8, I9: monotonicity -------------------------------------------------


@given(
    pot=_pots,
    max_members=_max_members,
    bids=st.tuples(_bids, _bids),
    data=st.data(),
)
@settings(max_examples=300)
def test_award_is_antitone_in_the_bid(pot, max_members, bids, data):
    k = data.draw(st.integers(min_value=0, max_value=max_members - 1))
    low, high = sorted(bids)
    assert compute_award(pot, max_members, low, k) >= compute_award(pot, max_members, high, k)
    if k > 0 and low < high:
        assert compute_award(pot, max_members, low, k) > compute_award(pot, max_members, high, k)


@given(pot=_pots, max_members=_max_members, bids=st.tuples(_bids, _bids))
@settings(max_examples=200)
def test_waiting_deduction_is_antitone_in_the_bid(pot, max_members, bids):
    low, high = sorted(bids)
    lower_bid_deduction = compute_deduction(pot, max_members, low, in_not_received=True)
    higher_bid_deduction = compute_deduction(pot, max_members, high, in_not_received=True)
    assert lower_bid_deduction >= higher_bid_deduction


@given(pot=_pots, max_members=_max_members, bid=_bids, data=st.data())
@settings(max_examples=300)
def test_award_is_antitone_in_the_waiting_count(pot, max_members, bid, data):
    fewer = data.draw(st.integers(min_value=0, max_value=max_members - 1))
    more = data.draw(st.integers(min_value=fewer, max_value=max_members - 1))
    assert compute_award(pot, max_members, bid, fewer) >= compute_award(pot, max_members, bid, more)


# --- I10: flat-payer invariance -------------------------------------------


@given(pot=_pots, max_members=_max_members, bid=_bids, k=st.integers(min_value=0, max_value=19))
@settings(max_examples=200)
def test_received_members_deduction_ignores_bid_and_waiting_count(pot, max_members, bid, k):
    baseline = compute_deduction(pot, max_members, 0, in_not_received=False)
    assert compute_deduction(pot, max_members, bid, in_not_received=False) == baseline


# --- I11, I12: envelope ---------------------------------------------------


@given(params=_rounds())
@settings(max_examples=400)
def test_award_stays_inside_its_envelope(params):
    pot, max_members, bid, k = params
    award = compute_award(pot, max_members, bid, k)
    minimum = ref.share(pot, max_members) * Fraction(max_members - k)
    assert Fraction(award) >= minimum - _tol(pot)
    assert award <= pot


@pytest.mark.xfail(
    reason="F4: exact at b=1 only once compute_award divides last",
    strict=False,
)
@given(pot=_pots, max_members=_max_members, data=st.data())
@settings(max_examples=200)
def test_award_lower_bound_is_exact_at_the_maximum_bid(pot, max_members, data):
    k = data.draw(st.integers(min_value=0, max_value=max_members - 1))
    award = compute_award(pot, max_members, Decimal("1.000"), k)
    assert award == pot * Decimal(max_members - k) / Decimal(max_members)


@given(params=_rounds())
@settings(max_examples=300)
def test_award_never_falls_below_one_share(params):
    pot, max_members, bid, k = params
    award = compute_award(pot, max_members, bid, k)
    assert Fraction(award) >= ref.share(pot, max_members) - _tol(pot)


@given(params=_rounds())
@settings(max_examples=300)
def test_waiting_deduction_never_exceeds_a_share(params):
    pot, max_members, bid, k = params
    waiting = compute_deduction(pot, max_members, bid, in_not_received=True)
    assert Fraction(waiting) <= ref.share(pot, max_members) + _tol(pot)


# --- I14, I15: the two bid extremes ---------------------------------------


@given(pot=_pots, max_members=_max_members, data=st.data())
@settings(max_examples=300)
def test_zero_bid_is_exactly_plain_rotating_savings(pot, max_members, data):
    k = data.draw(st.integers(min_value=0, max_value=max_members - 1))
    assert compute_award(pot, max_members, 0, k) == pot
    flat = pot / Decimal(max_members)
    assert compute_deduction(pot, max_members, 0, in_not_received=True) == flat
    assert compute_deduction(pot, max_members, 0, in_not_received=False) == flat


