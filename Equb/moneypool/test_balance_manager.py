from decimal import Decimal

import pytest

from .factories import make_full_equb_via_add_member as _make_full_equb
from .models import Bid, HighestBid
from .services.equb_service import place_bid
from .tasks import select_winner_task


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


