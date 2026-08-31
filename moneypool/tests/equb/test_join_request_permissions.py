from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import (
    EqubFactory,
    EqubJoinRequestFactory,
    FriendRequestFactory,
    UserFactory,
    make_forming_equb,
)
from moneypool.services.equb_service import add_member, place_bid
from moneypool.tasks import select_winner_task
from decimal import Decimal


@pytest.mark.django_db
class TestEqubJoinRequestPermissions:
    def test_sender_cannot_patch_their_own_join_request(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        requester = UserFactory()
        join_request = EqubJoinRequestFactory(equb=equb, sender=requester, receiver=equb.creator)
        client = make_authed_client(requester)
        response = client.patch(
            reverse("equbjoinrequest-detail", args=[join_request.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_outsider_cannot_patch_someone_elses_join_request(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        requester = UserFactory()
        join_request = EqubJoinRequestFactory(equb=equb, sender=requester, receiver=equb.creator)
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.patch(
            reverse("equbjoinrequest-detail", args=[join_request.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestEqubJoinRequestVotePermissions:
    def test_a_member_who_is_not_the_creator_can_vote(self, make_authed_client):
        equb, joined = make_forming_equb(max_members=4, members=3)
        member = next(m for m in joined if m != equb.creator)
        join_request = EqubJoinRequestFactory(equb=equb, sender=UserFactory(), receiver=equb.creator)

        response = make_authed_client(member).post(
            reverse("equbjoinrequest-vote", args=[join_request.pk]), {"approve": True}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_a_member_still_cannot_patch_the_request(self, make_authed_client):
        equb, joined = make_forming_equb(max_members=4, members=3)
        member = next(m for m in joined if m != equb.creator)
        join_request = EqubJoinRequestFactory(equb=equb, sender=UserFactory(), receiver=equb.creator)

        response = make_authed_client(member).patch(
            reverse("equbjoinrequest-detail", args=[join_request.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_a_non_member_cannot_vote(self, make_authed_client):
        equb, _ = make_forming_equb(max_members=4, members=3)
        join_request = EqubJoinRequestFactory(equb=equb, sender=UserFactory(), receiver=equb.creator)

        response = make_authed_client(UserFactory()).post(
            reverse("equbjoinrequest-vote", args=[join_request.pk]), {"approve": True}, format="json"
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_the_requester_cannot_vote_on_their_own_request(self, make_authed_client):
        equb, _ = make_forming_equb(max_members=4, members=3)
        requester = UserFactory()
        join_request = EqubJoinRequestFactory(equb=equb, sender=requester, receiver=equb.creator)

        response = make_authed_client(requester).post(
            reverse("equbjoinrequest-vote", args=[join_request.pk]), {"approve": True}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEqubJoinRequestTrustSignal:
    def test_trusted_by_is_the_members_who_are_friends_with_the_requester(self, make_authed_client):
        equb, joined = make_forming_equb(max_members=5, members=4)
        requester = UserFactory()
        trusting = joined[1:3]
        for member in trusting:
            member.friends.add(requester)
        EqubJoinRequestFactory(equb=equb, sender=requester, receiver=equb.creator)

        body = make_authed_client(equb.creator).get(
            reverse("equbjoinrequest-by-equb") + f"?equb={equb.pk}"
        ).json()

        assert {user['id'] for user in body[0]['trusted_by']} == {m.id for m in trusting}
        assert body[0]['trusted_by_count'] == len(trusting)

    def test_the_tally_reports_what_is_still_needed(self, make_authed_client):
        equb, joined = make_forming_equb(max_members=5, members=4)
        join_request = EqubJoinRequestFactory(equb=equb, sender=UserFactory(), receiver=equb.creator)
        member = next(m for m in joined if m != equb.creator)
        client = make_authed_client(member)
        client.post(
            reverse("equbjoinrequest-vote", args=[join_request.pk]), {"approve": True}, format="json"
        )

        body = client.get(reverse("equbjoinrequest-by-equb") + f"?equb={equb.pk}").json()

        assert body[0]['approvals'] == 1
        assert body[0]['rejections'] == 0
        assert body[0]['required_approvals'] == 3
        assert body[0]['current_user_vote'] is True
