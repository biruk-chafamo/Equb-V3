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


@pytest.mark.django_db
class TestSetupNextRoundClockInjection:
    def test_filling_the_equb_activates_it_and_schedules_the_first_round(self, live_updates):
        equb = EqubFactory(max_members=2, cycle=datetime.timedelta(minutes=10))
        new_member = UserFactory()

        fixed_now = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)
        clock = FixedClock(fixed_now)
        scheduler = RecordingScheduler()
        notifier = DjangoNotifier(clock=clock, live_updates=live_updates, scheduler=scheduler)

        add_member(equb, new_member, notifier=notifier, clock=clock)

        equb.refresh_from_db()
        assert equb.is_active is True
        assert scheduler.scheduled == [(equb.name, fixed_now + datetime.timedelta(minutes=10))]
        assert equb.balance_manager.current_round_start_date == fixed_now


@pytest.mark.django_db
class TestPlaceBid:
    def test_first_bid_notifies_every_member_and_pushes_a_live_update(self, notifier, live_updates):
        equb = EqubFactory(max_members=2)
        members = list(equb.members.all())
        bidder = members[0]

        bid = place_bid(bidder, equb, Decimal("0.100"), notifier=notifier)

        notified = OutBidNotification.objects.filter(equb=equb)
        assert set(notified.values_list("receiver", flat=True)) == {m.id for m in members}
        assert all(n.previous_highest_bid is None for n in notified)
        assert all(n.new_highest_bid == bid for n in notified)
        assert live_updates.equb_ids == [equb.id]

    def test_lower_bid_neither_notifies_nor_pushes(self, notifier, live_updates):
        equb = EqubFactory(max_members=3)
        members = list(equb.members.all())
        place_bid(members[0], equb, Decimal("0.500"), notifier=notifier)

        rows_after_first_bid = OutBidNotification.objects.filter(equb=equb).count()
        live_updates.equb_ids.clear()

        place_bid(members[0], equb, Decimal("0.100"), notifier=notifier)

        assert OutBidNotification.objects.filter(equb=equb).count() == rows_after_first_bid
        assert live_updates.equb_ids == []
