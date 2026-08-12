from decimal import Decimal
from fractions import Fraction

from django.urls import reverse
from hypothesis import HealthCheck, given, settings, strategies as st
from rest_framework import status

import pytest

from moneypool.domain import settlement_reference as ref
from moneypool.domain.settlement import compute_deduction
from moneypool.tests.factories import (
    EqubFactory,
    UserFactory,
    make_full_equb_via_join_requests as _make_full_equb,
)
from moneypool.models import BalanceManager, ServiceChoices
from moneypool.services.equb_service import add_member, place_bid
from moneypool.services.settlement_service import (
    calculate_losers_deductions,
    calculate_winners_award,
    setup_next_round,
)
from moneypool.tasks import select_winner_task

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
        awards.append(calculate_winners_award(manager, round_number))
        deductions.append(
            {
                member.pk: calculate_losers_deductions(manager, member, round_number)
                for member in equb.members.all()
                if member != winner
            }
        )

        setup_next_round(manager)
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


@pytest.mark.django_db
@given(max_members=_sizes, data=st.data())
@settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_the_ledger_of_a_whole_equb_matches_the_closed_form(max_members, data):
    amount = data.draw(_amounts)
    bid_plan = data.draw(st.lists(_bids, min_size=max_members, max_size=max_members))

    members, winners, bids, waiting_counts, awards, deductions = _run_equb(
        max_members, amount, bid_plan
    )
    tolerance = Fraction(amount) * _RELATIVE_TOLERANCE * max_members
    nets, win_round = _nets(members, winners, awards, deductions, amount, max_members)
    share = ref.share(amount, max_members)

    # I16: the winner of round r leaves exactly N - r members still waiting
    assert waiting_counts == [max_members - r for r in range(1, max_members + 1)]

    # I17: the win schedule is a permutation of the membership
    assert len(winners) == max_members
    assert {winner.pk for winner in winners} == {member.pk for member in members}

    for member in members:
        round_number = win_round[member.pk]
        # I18
        expected = ref.member_net(amount, max_members, bids, round_number)
        assert abs(nets[member.pk] - expected) <= tolerance
        # I20
        if bids[round_number - 1] == 0:
            assert nets[member.pk] >= -tolerance
        # I21
        worst_case = -share * Fraction(bids[round_number - 1]) * Fraction(max_members - round_number)
        assert nets[member.pk] >= worst_case - tolerance

    # I19
    assert abs(sum(nets.values(), Fraction(0))) <= tolerance


# --- I22: patience never hurts a non-bidder -------------------------------


@given(
    amount=_amounts,
    max_members=st.integers(min_value=2, max_value=20),
    data=st.data(),
)
@settings(max_examples=200)
def test_winning_later_never_hurts_a_member_who_does_not_bid(amount, max_members, data):
    bids = data.draw(st.lists(_bids, min_size=max_members, max_size=max_members))
    earlier = data.draw(st.integers(min_value=1, max_value=max_members))
    later = data.draw(st.integers(min_value=earlier, max_value=max_members))
    quiet = list(bids)
    quiet[earlier - 1] = 0
    quiet[later - 1] = 0

    assert ref.member_net(amount, max_members, quiet, later) >= ref.member_net(
        amount, max_members, quiet, earlier
    )


# --- I27: the round's winner is never charged -----------------------------


@pytest.mark.django_db
class TestWinnerIsNeverCharged:
    def test_winner_cannot_send_a_payment_request_for_their_own_round(self, make_authed_client):
        equb, (user0, user1) = _make_full_equb(max_members=2)
        client0 = make_authed_client(user0)
        client0.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.900"},
        )
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        assert equb.balance_manager.latest_winner() == user0

        payment_method = user0.selected_payment_methods.filter(service=ServiceChoices.CASH).first()
        response = client0.post(
            reverse("paymentconfirmationrequest-list"),
            {
                "equb": reverse("equb-detail", args=[equb.pk]),
                "round": 1,
                "payment_method": reverse("paymentmethod-detail", args=[payment_method.pk]),
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()


# --- F1: the displayed award is not the cash the winner receives ----------


@pytest.mark.django_db
@pytest.mark.xfail(
    reason="F1: get_current_award reports the gross award; the winner receives one share less",
    strict=False,
)
def test_displayed_award_equals_the_cash_the_winner_receives(make_authed_client):
    equb, (user0, user1) = _make_full_equb(max_members=2, amount=Decimal("100.00"))
    client0 = make_authed_client(user0)
    client0.post(
        reverse("bid-list"),
        {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.900"},
    )
    select_winner_task.now(equb.name)
    equb.refresh_from_db()
    manager = BalanceManager.objects.get(equb=equb)

    displayed = calculate_winners_award(manager, 1)
    collected = sum(
        calculate_losers_deductions(manager, member, 1)
        for member in equb.members.all()
        if member != manager.latest_winner()
    )
    assert displayed == collected
