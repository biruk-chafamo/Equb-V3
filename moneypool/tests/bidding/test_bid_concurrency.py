import threading
from decimal import Decimal

import pytest
from django.db import connection
from django.test import TransactionTestCase

from moneypool.tests.factories import EqubFactory, UserFactory
from moneypool.models import Bid, HighestBid, User
from moneypool.services.equb_service import add_member


class HighestBidRaceConditionTest(TransactionTestCase):
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Bid.is_highest_bid() decides on a stale read and "
            "make_highest_bid() writes unconditionally; needs select_for_update() "
            "on HighestBid so the compare and the write happen under one lock"
        ),
    )
    def test_concurrent_bids_keep_the_actual_highest_one(self):
        equb = EqubFactory(max_members=3)
        low_bidder = UserFactory()
        high_bidder = UserFactory()
        add_member(equb, low_bidder)
        add_member(equb, high_bidder)
        equb.refresh_from_db()
        round_number = 1

        both_read_barrier = threading.Barrier(2)
        high_bid_written = threading.Event()

        def place_bid_racily(user, amount, *, write_after_event=None, set_event_after_write=None):
            bid = Bid.objects.create(equb=equb, user=user, round=round_number, amount=amount)
            highest_bid = HighestBid.objects.get(equb=equb, round=round_number)
            current_highest_amount = highest_bid.bid.amount if highest_bid.bid else None
            is_higher = current_highest_amount is None or bid.amount > current_highest_amount

            both_read_barrier.wait()  # neither thread writes until both have read

            if write_after_event is not None:
                write_after_event.wait()

            if is_higher:
                highest_bid.bid = bid
                highest_bid.save()

            if set_event_after_write is not None:
                set_event_after_write.set()

            connection.close()

        high_thread = threading.Thread(
            target=place_bid_racily,
            args=(high_bidder, Decimal("0.900")),
            kwargs={"set_event_after_write": high_bid_written},
        )
        low_thread = threading.Thread(
            target=place_bid_racily,
            args=(low_bidder, Decimal("0.100")),
            kwargs={"write_after_event": high_bid_written},
        )

        high_thread.start()
        low_thread.start()
        high_thread.join()
        low_thread.join()

        final_highest_bid = HighestBid.objects.get(equb=equb, round=round_number)
        assert final_highest_bid.bid.amount == Decimal("0.900"), (
            "HighestBid must record the genuinely highest bid (0.900), got "
            f"{final_highest_bid.bid.amount}: the later, lower bid overwrote it "
            "on the strength of a stale read (lost update). Fix by taking a lock "
            "on the HighestBid row (select_for_update) and re-comparing under it, "
            "so the winning bid cannot be made irrelevant by a concurrent lower one"
        )
