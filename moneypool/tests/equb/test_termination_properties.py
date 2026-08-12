from hypothesis import HealthCheck, given, settings, strategies as st

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory
from moneypool.services.equb_service import add_member
from moneypool.services.settlement_service import setup_next_round
from moneypool.tasks import select_winner_task


@pytest.mark.django_db
@given(max_members=st.integers(min_value=2, max_value=6))
@settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_equb_completes_in_exactly_max_members_rounds(max_members):
    equb = EqubFactory(max_members=max_members)
    for _ in range(max_members - 1):
        add_member(equb, UserFactory())
    equb.refresh_from_db()
    assert equb.is_active is True

    rounds_run = 0
    for _ in range(max_members):
        assert equb.is_completed is False
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        setup_next_round(equb.balance_manager)
        equb.refresh_from_db()
        rounds_run += 1

    assert rounds_run == max_members
    assert equb.balance_manager.finished_rounds == max_members
    assert equb.is_completed is True
    assert equb.balance_manager.received.count() == max_members
