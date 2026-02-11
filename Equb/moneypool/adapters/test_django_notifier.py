import datetime
from decimal import Decimal

import pytest

from .django_notifier import DjangoNotifier
from ..factories import (
    BidFactory,
    EqubFactory,
    PaymentConfirmationRequestFactory,
    UserFactory,
)
from ..fakes import FixedClock, RecordingLiveUpdates, RecordingScheduler
from ..models import (
    NewEqubNotification,
    NewMemberNotification,
    NewPaymentConfirmationRequestNotification,
    NewRoundNotification,
    OutBidNotification,
)

FIXED_NOW = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def live_updates():
    return RecordingLiveUpdates()


@pytest.fixture
def scheduler():
    return RecordingScheduler()


@pytest.fixture
def notifier(live_updates, scheduler):
    return DjangoNotifier(
        clock=FixedClock(FIXED_NOW), live_updates=live_updates, scheduler=scheduler
    )


@pytest.mark.django_db
class TestEqubCreated:
    @pytest.mark.parametrize("friend_count", [0, 1, 3])
    def test_fans_out_to_every_friend_of_the_creator(self, notifier, friend_count):
        creator = UserFactory()
        # Friends are added *after* the equb exists on purpose. EqubFactory
        # routes through equb_service.create_equb (see factories.py), which
        # already fires equb_created once via the default notifier -- with a
        # friendless creator that call is a no-op, so the rows counted below
        # come only from the explicit call under test.
        equb = EqubFactory(creator=creator, is_private=False)
        friends = [UserFactory() for _ in range(friend_count)]
        for friend in friends:
            creator.friends.add(friend)
        assert NewEqubNotification.objects.filter(equb=equb).count() == 0

        notifier.equb_created(equb)

        notified = NewEqubNotification.objects.filter(equb=equb)
        assert notified.count() == friend_count
        assert set(notified.values_list("receiver", flat=True)) == {f.id for f in friends}

    def test_private_equb_notifies_nobody(self, notifier):
        creator = UserFactory()
        creator.friends.add(UserFactory())
        equb = EqubFactory(creator=creator, is_private=True)

        notifier.equb_created(equb)

        assert NewEqubNotification.objects.filter(equb=equb).count() == 0


@pytest.mark.django_db
class TestMemberJoined:
    def test_notifies_prior_members_only(self, notifier):
        equb = EqubFactory(max_members=3)
        new_member = UserFactory()
        equb.members.add(new_member)

        notifier.member_joined(equb, new_member)

        receivers = set(
            NewMemberNotification.objects.filter(equb=equb).values_list("receiver", flat=True)
        )
        assert receivers == {equb.creator.id}
        assert new_member.id not in receivers


@pytest.mark.django_db
class TestSchedulingEvents:
    def test_activation_schedules_winner_selection_one_cycle_out(self, notifier, scheduler):
        cycle = datetime.timedelta(minutes=10)
        equb = EqubFactory(cycle=cycle)

        notifier.equb_activated(equb)

        assert scheduler.scheduled == [(equb.name, FIXED_NOW + cycle)]

