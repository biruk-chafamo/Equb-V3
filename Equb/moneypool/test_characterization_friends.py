from django.urls import reverse
from rest_framework import status

import pytest

from .factories import UserFactory, FriendRequestFactory


@pytest.mark.django_db
class TestFriendRequest:
    def test_send_friend_request(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        client = make_authed_client(sender)
        data = {"receiver": reverse("user-detail", args=[receiver.pk])}
        response = client.post(reverse("friendrequest-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

