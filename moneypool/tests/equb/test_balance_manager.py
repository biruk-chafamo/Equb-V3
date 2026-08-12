from decimal import Decimal

import pytest

from moneypool.tests.factories import make_full_equb_via_add_member as _make_full_equb
from moneypool.models import Bid, HighestBid
from moneypool.services.equb_service import place_bid
from moneypool.tasks import select_winner_task


@pytest.mark.django_db
class TestSelectWinnerNeverRepeats:
    def test_no_member_wins_twice_across_a_full_multi_round_equb(self):
        equb, members = _make_full_equb(max_members=4)

        winners = []
        for _ in range(equb.max_members):
            select_winner_task.now(equb.name)
            equb.refresh_from_db()
            winners.append(equb.balance_manager.latest_winner())
            equb.balance_manager.setup_next_round()
            equb.refresh_from_db()

        assert len(winners) == 4
        assert len(set(winners)) == 4  # no repeated winners
        assert set(winners) == set(members)  # everyone won exactly once
        assert equb.balance_manager.received.count() == 4
        assert equb.is_completed is True


@pytest.mark.django_db
class TestBidRankingAdapter:
    def test_is_highest_bid_true_for_first_bid(self):
        equb, members = _make_full_equb(max_members=2)
        bid = Bid.objects.create(equb=equb, user=members[0], round=1, amount=Decimal("0.100"))
        assert bid.is_highest_bid() is True

    def test_is_highest_bid_false_for_lower_bid(self):
        equb, members = _make_full_equb(max_members=3)
        first = place_bid(members[0], equb, Decimal("0.500"))
        assert first.is_highest_bid() is False
        lower = Bid.objects.create(equb=equb, user=members[1], round=1, amount=Decimal("0.100"))
        assert lower.is_highest_bid() is False

    def test_make_highest_bid_updates_highest_bid_record(self):
        equb, members = _make_full_equb(max_members=2)
        bid = Bid.objects.create(equb=equb, user=members[0], round=1, amount=Decimal("0.300"))
        assert bid.is_highest_bid() is True
        bid.make_highest_bid()
        assert HighestBid.objects.get(equb=equb, round=1).bid == bid
