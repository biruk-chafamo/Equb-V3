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

    def test_cannot_friend_request_self(self, make_authed_client):
        user = UserFactory()
        client = make_authed_client(user)
        data = {"receiver": reverse("user-detail", args=[user.pk])}
        response = client.post(reverse("friendrequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()

    def test_duplicate_pending_request_rejected(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        FriendRequestFactory(sender=sender, receiver=receiver)
        client = make_authed_client(sender)
        data = {"receiver": reverse("user-detail", args=[receiver.pk])}
        response = client.post(reverse("friendrequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()

    def test_cannot_request_existing_friend(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        sender.friends.add(receiver)
        client = make_authed_client(sender)
        data = {"receiver": reverse("user-detail", args=[receiver.pk])}
        response = client.post(reverse("friendrequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()

