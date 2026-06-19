from decimal import Decimal
from fractions import Fraction

from django.urls import reverse
from hypothesis import HealthCheck, given, settings, strategies as st
from rest_framework import status

import pytest

from .domain import settlement_reference as ref
from .domain.settlement import compute_deduction
from .factories import (
    EqubFactory,
    UserFactory,
    make_full_equb_via_join_requests as _make_full_equb,
)
from .models import BalanceManager, ServiceChoices
from .services.equb_service import add_member, place_bid
from .tasks import select_winner_task

_bids = st.one_of(
    st.just(0),
    st.decimals(min_value=Decimal("0.001"), max_value=Decimal("1.000"), places=3),
)
_amounts = st.decimals(min_value=Decimal("1.00"), max_value=Decimal("100000.00"), places=2)
_sizes = st.integers(min_value=2, max_value=5)

_RELATIVE_TOLERANCE = Fraction(1, 10 ** 20)


def _run_equb(max_members, amount, bid_plan):
    """Runs a full equb and returns (members, winners, bids, waiting_counts, awards, deductions)."""
    equb = EqubFactory(max_members=max_members, amount=amount)
    for _ in range(max_members - 1):
        add_member(equb, UserFactory())
    equb.refresh_from_db()

    winners, bids, waiting_counts, awards, deductions = [], [], [], [], []

    for round_number in range(1, max_members + 1):
        manager = BalanceManager.objects.get(equb=equb)
        not_received = list(equb.members.all().difference(manager.received.all()))

        planned = bid_plan[round_number - 1]
        if planned > 0 and len(not_received) > 1:
            place_bid(min(not_received, key=lambda user: user.pk), equb, planned)
            bids.append(planned)
        else:
            bids.append(0)

        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        manager = BalanceManager.objects.get(equb=equb)

        winner = manager.latest_winner()
        winners.append(winner)
        waiting_counts.append(equb.members.all().difference(manager.received.all()).count())
        awards.append(manager.calculate_winners_award(round_number))
        deductions.append(
            {
                member.pk: manager.calculate_losers_deductions(member, round_number)
                for member in equb.members.all()
                if member != winner
            }
        )

        manager.setup_next_round()
        equb.refresh_from_db()

    return list(equb.members.all()), winners, bids, waiting_counts, awards, deductions


def _nets(members, winners, awards, deductions, amount, max_members):
    share = compute_deduction(amount, max_members, 0, in_not_received=False)
    win_round = {winner.pk: index + 1 for index, winner in enumerate(winners)}
    nets = {}
    for member in members:
        round_number = win_round[member.pk]
        cash_in = Fraction(awards[round_number - 1]) - Fraction(share)
        cash_out = sum(
            (Fraction(charges[member.pk]) for charges in deductions if member.pk in charges),
            Fraction(0),
        )
        nets[member.pk] = cash_in - cash_out
    return nets, win_round


# --- I16, I17, I18, I19, I20, I21 -----------------------------------------


