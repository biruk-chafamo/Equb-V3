from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, EqubJoinRequestFactory, FriendRequestFactory, UserFactory
from moneypool.services.equb_service import add_member, place_bid
from moneypool.tasks import select_winner_task
from decimal import Decimal


@pytest.mark.django_db
class TestFriendRequestPermissions:
    def test_sender_cannot_patch_their_own_friend_request(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        friend_request = FriendRequestFactory(sender=sender, receiver=receiver)
        client = make_authed_client(sender)
        response = client.patch(
            reverse("friendrequest-detail", args=[friend_request.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_outsider_cannot_patch_someone_elses_friend_request(self, make_authed_client):
        sender = UserFactory()
        receiver = UserFactory()
        friend_request = FriendRequestFactory(sender=sender, receiver=receiver)
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.patch(
            reverse("friendrequest-detail", args=[friend_request.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserProfilePermissions:
    def test_cannot_edit_another_users_profile(self, make_authed_client):
        target = UserFactory()
        other = UserFactory()
        client = make_authed_client(other)
        response = client.patch(
            reverse("user-detail", args=[target.pk]), {"first_name": "Hijacked"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_can_edit_own_profile(self, make_authed_client):
        user = UserFactory()
        client = make_authed_client(user)
        response = client.patch(reverse("user-detail", args=[user.pk]), {"first_name": "NewName"})
        assert response.status_code == status.HTTP_200_OK
