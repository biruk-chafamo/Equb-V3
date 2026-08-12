from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory, make_full_equb_via_add_member as _make_full_equb
from moneypool.services.equb_service import place_bid
from moneypool.tasks import select_winner_task


@pytest.mark.django_db
class TestFriendRequestAlreadyFriend:
    def test_cannot_send_friend_request_to_existing_friend(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        sender.friends.add(receiver)
        client = make_authed_client(sender)
        response = client.post(
            reverse("friendrequest-list"), {"receiver": reverse("user-detail", args=[receiver.pk])}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()
