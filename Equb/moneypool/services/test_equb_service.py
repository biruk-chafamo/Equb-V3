import datetime
from decimal import Decimal

import pytest

from .equb_service import add_member, create_equb, place_bid
from ..adapters.django_notifier import DjangoNotifier
from ..factories import EqubFactory, UserFactory
from ..fakes import FixedClock, RecordingScheduler
from ..models import NewEqubNotification, NewMemberNotification, OutBidNotification


@pytest.mark.django_db
class TestCreateEqub:
    def test_public_equb_creation_notifies_every_friend(self, notifier):
        creator = UserFactory()
        friends = [UserFactory() for _ in range(3)]
        for friend in friends:
            creator.friends.add(friend)

        equb = create_equb(
            creator=creator,
            name="svc_test_equb",
            amount=Decimal("100.00"),
            max_members=2,
            cycle=datetime.timedelta(minutes=10),
            notifier=notifier,
            is_private=False,
        )

        notified = NewEqubNotification.objects.filter(equb=equb)
        assert notified.count() == len(friends)
        assert set(notified.values_list("receiver", flat=True)) == {f.id for f in friends}
        # the creator announces to friends, and is not announced to
        assert creator.id not in set(notified.values_list("receiver", flat=True))

