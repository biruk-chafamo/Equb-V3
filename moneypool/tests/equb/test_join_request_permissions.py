from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, EqubJoinRequestFactory, FriendRequestFactory, UserFactory
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
