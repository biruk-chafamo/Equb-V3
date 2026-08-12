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

    def test_accept_makes_users_mutual_friends(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        friend_request = FriendRequestFactory(sender=sender, receiver=receiver)
        client = make_authed_client(receiver)
        response = client.patch(
            reverse("friendrequest-detail", args=[friend_request.pk]),
            {"is_accepted": True},
        )
        assert response.status_code == status.HTTP_200_OK
        assert receiver in sender.friends.all()
        assert sender in receiver.friends.all()

    @pytest.mark.xfail(reason="Rejecting request is not yet implemented")
    def test_rejecting_a_friend_request(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        friend_request = FriendRequestFactory(sender=sender, receiver=receiver)
        client = make_authed_client(receiver)
        response = client.patch(
            reverse("friendrequest-detail", args=[friend_request.pk]),
            {"is_rejected": True},
        )
        assert response.status_code == status.HTTP_200_OK
        assert receiver not in sender.friends.all()

    def test_received_action_lists_pending_requests(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        FriendRequestFactory(sender=sender, receiver=receiver)
        client = make_authed_client(receiver)
        response = client.get(reverse("friendrequest-received"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 1
