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


