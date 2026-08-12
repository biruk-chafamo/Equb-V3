import datetime

import pytest
from django.utils import timezone

from moneypool.tests.factories import make_full_equb_via_add_member as _make_full_equb


@pytest.mark.django_db
class TestTimeLeftTillNextRound:
    def test_all_zero_before_the_first_round_starts(self):
        equb, _ = _make_full_equb(max_members=2)
        manager = equb.balance_manager
        manager.current_round_start_date = None
        manager.save()

        assert manager.time_left_till_next_round() == {
            "days": 0,
            "hours": 0,
            "minutes": 0,
            "seconds": 0,
        }

    def test_splits_a_mid_cycle_remainder_into_its_units(self):
        equb, _ = _make_full_equb(max_members=2)
        equb.cycle = datetime.timedelta(days=7)
        equb.save()
        manager = equb.balance_manager
        # 6d 20h 59m 59s out, so every unit lands at its maximum
        manager.current_round_start_date = (
            timezone.now() - datetime.timedelta(days=7) + datetime.timedelta(
                days=6, hours=20, minutes=59, seconds=59
            )
        )
        manager.save()

        left = manager.time_left_till_next_round()

        assert left["days"] == 6
        assert left["hours"] == 20
        assert left["minutes"] == 59
        assert 55 <= left["seconds"] <= 59

    def test_seconds_never_exceed_a_minute(self):
        equb, _ = _make_full_equb(max_members=2)
        equb.cycle = datetime.timedelta(days=7)
        equb.save()
        manager = equb.balance_manager
        manager.current_round_start_date = timezone.now()
        manager.save()

        left = manager.time_left_till_next_round()

        assert 0 <= left["seconds"] < 60
        assert 0 <= left["minutes"] < 60
        assert 0 <= left["hours"] < 24

    def test_every_unit_is_an_integer(self):
        equb, _ = _make_full_equb(max_members=2)
        manager = equb.balance_manager
        manager.current_round_start_date = timezone.now()
        manager.save()

        for value in manager.time_left_till_next_round().values():
            assert isinstance(value, int)

    def test_an_overdue_round_reports_negative_days(self):
        equb, _ = _make_full_equb(max_members=2)
        equb.cycle = datetime.timedelta(days=1)
        equb.save()
        manager = equb.balance_manager
        manager.current_round_start_date = timezone.now() - datetime.timedelta(days=3)
        manager.save()

        left = manager.time_left_till_next_round()

        assert left["days"] < 0
        assert 0 <= left["seconds"] < 60
