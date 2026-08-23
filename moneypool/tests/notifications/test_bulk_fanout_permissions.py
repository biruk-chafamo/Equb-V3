"""The bulk fan-out grants exactly what the per-row signal used to."""
import pytest

from moneypool.models import (
    NewEqubNotification,
    NewMemberNotification,
    NewRoundNotification,
    OutBidNotification,
)
from moneypool.tests.factories import BidFactory, make_full_equb_via_add_member


@pytest.mark.django_db
class TestFanOutGrantsPermissions:
    def test_every_member_may_change_their_own_out_bid_notification(self):
        equb, members = make_full_equb_via_add_member(4)
        bid = BidFactory(equb=equb, user=members[0])

        OutBidNotification.notify(equb, None, bid)

        notifications = OutBidNotification.objects.filter(equb=equb)
        assert notifications.count() == len(members)
        for notification in notifications:
            receiver = notification.receiver
            assert receiver.has_perm('moneypool.change_outbidnotification')
            assert receiver.has_perm('change_outbidnotification', notification)

    def test_a_member_may_not_change_someone_elses_notification(self):
        equb, members = make_full_equb_via_add_member(4)
        bid = BidFactory(equb=equb, user=members[0])

        OutBidNotification.notify(equb, None, bid)

        first, second = OutBidNotification.objects.filter(equb=equb)[:2]
        assert not second.receiver.has_perm('change_outbidnotification', first)

    def test_new_round_notifications_are_granted(self):
        equb, members = make_full_equb_via_add_member(3)

        NewRoundNotification.notify(equb)

        for notification in NewRoundNotification.objects.filter(equb=equb):
            assert notification.receiver.has_perm(
                'change_newroundnotification', notification)

    def test_a_new_member_is_not_notified_of_their_own_arrival(self):
        equb, members = make_full_equb_via_add_member(3)
        newcomer = members[-1]

        NewMemberNotification.notify(equb, newcomer)

        receivers = {n.receiver_id for n in NewMemberNotification.objects.filter(equb=equb)}
        assert newcomer.id not in receivers
        assert receivers == {m.id for m in members} - {newcomer.id}

    def test_re_granting_the_same_permission_is_harmless(self):
        equb, members = make_full_equb_via_add_member(3)

        NewRoundNotification.notify(equb)
        NewRoundNotification.notify(equb)

        for notification in NewRoundNotification.objects.filter(equb=equb):
            assert notification.receiver.has_perm(
                'change_newroundnotification', notification)

    def test_a_creator_with_no_friends_notifies_nobody(self):
        equb, _members = make_full_equb_via_add_member(2)

        NewEqubNotification.notify(equb)

        assert not NewEqubNotification.objects.filter(equb=equb).exists()
