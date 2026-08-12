import datetime
from decimal import Decimal

import pytest

from moneypool.adapters.django_notifier import DjangoNotifier
from moneypool.models import HighestBid, NewRoundNotification, Win
from moneypool.services.equb_service import place_bid
from moneypool.services.settlement_service import (
    calculate_losers_deductions,
    calculate_winners_award,
    select_winner,
    setup_next_round,
)
from moneypool.tests.factories import make_full_equb_via_add_member
from moneypool.tests.fakes import FixedClock, RecordingLiveUpdates, RecordingScheduler

FIXED_NOW = datetime.datetime(2025, 6, 1, 9, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def fixed_clock():
    return FixedClock(FIXED_NOW)


@pytest.fixture
def wired(fixed_clock):
    live_updates = RecordingLiveUpdates()
    scheduler = RecordingScheduler()
    notifier = DjangoNotifier(
        clock=fixed_clock, live_updates=live_updates, scheduler=scheduler
    )
    return notifier, scheduler, live_updates


@pytest.mark.django_db
class TestSelectWinner:
    def test_highest_bidder_wins_and_enters_payment_stage(self, notifier):
        equb, members = make_full_equb_via_add_member(3)
        place_bid(members[1], equb, Decimal("0.200"), notifier=notifier)

        winner = select_winner(equb.balance_manager)

        equb.refresh_from_db()
        assert winner == members[1]
        assert equb.is_in_payment_stage is True
        assert winner in equb.balance_manager.received.all()

    def test_without_a_bid_a_waiting_member_still_wins(self):
        equb, members = make_full_equb_via_add_member(3)

        winner = select_winner(equb.balance_manager)

        assert winner in members
        assert equb.balance_manager.wins.count() == 1

    def test_a_previous_winner_cannot_win_again(self, notifier):
        equb, members = make_full_equb_via_add_member(3)
        first = select_winner(equb.balance_manager)
        setup_next_round(equb.balance_manager, notifier=notifier)

        second = select_winner(equb.balance_manager)

        assert second != first
        assert {first, second} <= set(members)

    def test_returns_none_once_every_member_has_received(self):
        equb, members = make_full_equb_via_add_member(2)
        for _ in range(len(members)):
            select_winner(equb.balance_manager)

        assert select_winner(equb.balance_manager) is None
        assert equb.balance_manager.received.count() == len(members)
        assert Win.objects.filter(winning_equb_managers=equb.balance_manager).count() == 2


@pytest.mark.django_db
class TestSetupNextRound:
    def test_advances_the_round_and_leaves_the_payment_stage(self, notifier):
        equb, _ = make_full_equb_via_add_member(3)
        select_winner(equb.balance_manager)

        setup_next_round(equb.balance_manager, notifier=notifier)

        equb.refresh_from_db()
        assert equb.balance_manager.finished_rounds == 1
        assert equb.is_in_payment_stage is False
        assert equb.is_completed is False

    def test_opens_a_highest_bid_row_for_the_new_round(self, notifier):
        equb, _ = make_full_equb_via_add_member(3)
        select_winner(equb.balance_manager)

        setup_next_round(equb.balance_manager, notifier=notifier)

        assert HighestBid.objects.filter(equb=equb, round=2).exists()

    def test_notifies_every_member_of_the_new_round(self, notifier):
        equb, members = make_full_equb_via_add_member(3)
        select_winner(equb.balance_manager)

        setup_next_round(equb.balance_manager, notifier=notifier)

        notified = NewRoundNotification.objects.filter(equb=equb)
        assert set(notified.values_list("receiver", flat=True)) == {m.id for m in members}

    def test_injected_clock_sets_the_round_start_date(self, wired, fixed_clock):
        notifier, _, _ = wired
        equb, _ = make_full_equb_via_add_member(3)
        select_winner(equb.balance_manager)

        setup_next_round(equb.balance_manager, notifier=notifier, clock=fixed_clock)

        equb.balance_manager.refresh_from_db()
        assert equb.balance_manager.current_round_start_date == FIXED_NOW

    def test_injected_clock_drives_the_next_scheduled_selection(self, wired, fixed_clock):
        notifier, scheduler, _ = wired
        equb, _ = make_full_equb_via_add_member(3)
        select_winner(equb.balance_manager)
        scheduler.scheduled.clear()

        setup_next_round(equb.balance_manager, notifier=notifier, clock=fixed_clock)

        assert scheduler.scheduled == [(equb.name, FIXED_NOW + equb.cycle)]

    def test_final_round_completes_the_equb_without_opening_another(self, notifier):
        equb, _ = make_full_equb_via_add_member(2)
        for _ in range(2):
            select_winner(equb.balance_manager)
            setup_next_round(equb.balance_manager, notifier=notifier)

        equb.refresh_from_db()
        assert equb.is_completed is True
        assert equb.end_date is not None
        assert HighestBid.objects.filter(equb=equb, round=3).exists() is False


@pytest.mark.django_db
class TestAwardAndDeductions:
    def test_zero_bid_pays_out_the_whole_pot(self):
        equb, _ = make_full_equb_via_add_member(4)
        select_winner(equb.balance_manager)

        assert calculate_winners_award(equb.balance_manager, 1) == equb.amount

    def test_bidding_discounts_the_award(self, notifier):
        equb, members = make_full_equb_via_add_member(4)
        place_bid(members[0], equb, Decimal("0.100"), notifier=notifier)
        select_winner(equb.balance_manager)

        assert calculate_winners_award(equb.balance_manager, 1) < equb.amount

    def test_waiting_members_pay_less_than_those_who_received(self, notifier):
        equb, members = make_full_equb_via_add_member(4)
        place_bid(members[0], equb, Decimal("0.100"), notifier=notifier)
        winner = select_winner(equb.balance_manager)
        waiting = next(m for m in members if m != winner)

        assert calculate_losers_deductions(equb.balance_manager, waiting, 1) < equb.amount / 4
        assert calculate_losers_deductions(equb.balance_manager, winner, 1) == equb.amount / 4

    def test_round_conserves_the_pot(self, notifier):
        equb, members = make_full_equb_via_add_member(4)
        place_bid(members[0], equb, Decimal("0.100"), notifier=notifier)
        winner = select_winner(equb.balance_manager)

        collected = sum(
            calculate_losers_deductions(equb.balance_manager, m, 1)
            for m in members
            if m != winner
        )
        award = calculate_winners_award(equb.balance_manager, 1)
        share = equb.amount / equb.max_members

        assert collected + share == award
