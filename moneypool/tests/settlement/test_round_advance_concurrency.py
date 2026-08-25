"""Two callers can advance the same round at once."""
import threading

from django.db import connection
from django.test import TransactionTestCase

from moneypool.models import BalanceManager, HighestBid
from moneypool.services.settlement_service import setup_next_round
from moneypool.tests.factories import make_full_equb_via_add_member


class RoundAdvanceRaceConditionTest(TransactionTestCase):
    def test_two_concurrent_advances_do_not_lose_a_round(self):
        equb, _members = make_full_equb_via_add_member(4)
        manager = equb.balance_manager
        starting_round = manager.finished_rounds

        both_read_barrier = threading.Barrier(2)

        def advance():
            local = BalanceManager.objects.select_related('equb').get(pk=manager.pk)
            both_read_barrier.wait()
            try:
                setup_next_round(local)
            finally:
                connection.close()

        threads = [threading.Thread(target=advance) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        manager.refresh_from_db()
        assert manager.finished_rounds == starting_round + 2, (
            f"expected two advances from {starting_round}, "
            f"got {manager.finished_rounds}"
        )

    def test_a_round_never_exists_without_its_highest_bid_row(self):
        equb, _members = make_full_equb_via_add_member(4)
        manager = equb.balance_manager

        setup_next_round(manager)
        manager.refresh_from_db()

        assert HighestBid.objects.filter(
            equb=equb, round=manager.finished_rounds + 1
        ).exists()
