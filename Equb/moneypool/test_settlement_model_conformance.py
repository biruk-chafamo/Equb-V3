from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from hypothesis import given, settings, strategies as st

from .domain import validation
from .domain.settlement import compute_award, compute_deduction
from .domain.test_settlement_invariants import (
    BID_MAX,
    BID_MIN,
    BID_PLACES,
    MAX_MEMBERS_MAX,
    MAX_MEMBERS_MIN,
    POT_MAX,
    POT_MIN,
    POT_PLACES,
    _bids,
    _max_members,
    _pots,
    _rounds,
)
from .models import Bid, Equb


def _limits(field, validator_class):
    return [v.limit_value for v in field.validators if isinstance(v, validator_class)]


# --- I24: generators match the bounds the system enforces -----------------


def test_pot_strategy_matches_the_amount_field():
    field = Equb._meta.get_field("amount")
    assert POT_PLACES == field.decimal_places
    assert POT_MAX == Decimal(10) ** (field.max_digits - field.decimal_places) - Decimal(
        1
    ).scaleb(-field.decimal_places)
    assert Decimal(str(_limits(field, MinValueValidator)[0])) == POT_MIN


def test_max_members_strategy_matches_the_enforced_range():
    field = Equb._meta.get_field("max_members")
    assert _limits(field, MinValueValidator)[0] == MAX_MEMBERS_MIN

    assert validation.is_max_members_too_low(MAX_MEMBERS_MIN) is False
    assert validation.is_max_members_too_low(MAX_MEMBERS_MIN - 1) is True
    assert validation.is_max_members_too_high(MAX_MEMBERS_MAX) is False
    assert validation.is_max_members_too_high(MAX_MEMBERS_MAX + 1) is True


def test_bid_strategy_matches_the_bid_field():
    field = Bid._meta.get_field("amount")
    assert BID_PLACES == field.decimal_places
    assert Decimal(str(_limits(field, MinValueValidator)[0])) == BID_MIN
    assert Decimal(str(_limits(field, MaxValueValidator)[0])) == BID_MAX


# --- I25: results fit the field they are written back to ------------------


