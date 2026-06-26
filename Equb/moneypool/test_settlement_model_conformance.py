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


