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

    def test_private_equb_creation_does_not_notify(self, notifier):
        creator = UserFactory()
        creator.friends.add(UserFactory())

        equb = create_equb(
            creator=creator,
            name="svc_test_equb",
            amount=Decimal("100.00"),
            max_members=2,
            cycle=datetime.timedelta(minutes=10),
            notifier=notifier,
            is_private=True,
        )

        assert NewEqubNotification.objects.filter(equb=equb).count() == 0

    def test_creation_neither_pushes_nor_schedules(self, notifier, live_updates, scheduler):
        creator = UserFactory()
        creator.friends.add(UserFactory())

        create_equb(
            creator=creator,
            name="svc_test_equb",
            amount=Decimal("100.00"),
            max_members=2,
            cycle=datetime.timedelta(minutes=10),
            notifier=notifier,
        )

        assert live_updates.equb_ids == []
        assert scheduler.scheduled == []

    def test_still_sets_up_structural_invariants(self, notifier):
        creator = UserFactory()
        equb = create_equb(
            creator=creator,
            name="svc_test_equb_2",
            amount=Decimal("100.00"),
            max_members=2,
            cycle=datetime.timedelta(minutes=10),
            notifier=notifier,
        )
        assert equb.balance_manager is not None
        assert equb.highest_bids.get(round=1) is not None
        assert creator in equb.members.all()


@pytest.mark.django_db
class TestAddMember:
    def test_notifies_existing_members_without_activating_when_not_full(self, notifier, scheduler):
        equb = EqubFactory(max_members=3)
        new_member = UserFactory()

        add_member(equb, new_member, notifier=notifier)

        notified = NewMemberNotification.objects.filter(equb=equb)
        # every member except the one who just joined
        assert set(notified.values_list("receiver", flat=True)) == {equb.creator.id}
        assert notified.first().new_member == new_member

        equb.refresh_from_db()
        assert equb.is_active is False
        assert scheduler.scheduled == []


