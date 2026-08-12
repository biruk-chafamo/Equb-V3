import threading
from decimal import Decimal

import pytest
from django.db import connection
from django.test import TransactionTestCase

from moneypool.tests.factories import EqubFactory, UserFactory
from moneypool.models import Bid, HighestBid, User
from moneypool.services.equb_service import add_member


class BankAccountRaceConditionTest(TransactionTestCase):
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "lost update: bank_account is read, mutated and saved back, "
            "so a concurrent credit is overwritten; needs F('bank_account') + amount "
            "(or select_for_update) to make the increment atomic"
        ),
    )
    def test_concurrent_credits_both_apply(self):
        """
        Two concurrent 10.00 credits must both land, leaving 20.00.

        Same underlying pattern (plain read -> mutate -> save, no locking),
        demonstrated against the simpler bank_account +=/save() case used by
        update_winner_account()/collect_money(). Both threads read the
        starting balance before either writes, so one credit is lost.
        """
        user = UserFactory(bank_account=Decimal("0.00"))
        user_id = user.pk
        both_read_barrier = threading.Barrier(2)

        def credit(amount):
            u = User.objects.get(pk=user_id)
            both_read_barrier.wait()  # neither writes until both have read the same starting value
            u.bank_account += amount
            u.save()
            connection.close()

        threads = [
            threading.Thread(target=credit, args=(Decimal("10.00"),)),
            threading.Thread(target=credit, args=(Decimal("10.00"),)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        user.refresh_from_db()
        assert user.bank_account == Decimal("20.00"), (
            "both 10.00 credits must be applied, leaving 20.00, got "
            f"{user.bank_account}:  one credit was overwritten by the other "
            "(lost update). Fix by making the increment atomic in the database: "
            "F('bank_account') + amount, or select_for_update on the User row"
        )
