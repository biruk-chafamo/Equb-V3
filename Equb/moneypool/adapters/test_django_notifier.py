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

