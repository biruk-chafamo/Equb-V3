from django.urls import reverse
from rest_framework import status

import pytest

from .factories import UserFactory, EqubFactory, EqubInviteRequestFactory


@pytest.mark.django_db
class TestCreateEqub:
    def test_create_equb_success(self, make_authed_client):
        user = UserFactory()
        client = make_authed_client(user)
        data = {
            "name": "characterization_equb",
            "max_members": 3,
            "amount": "100.00",
            "cycle": "00:10:00",
            "is_private": False,
        }
        response = client.post(reverse("equb-list"), data)

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["name"] == "characterization_equb"
        assert body["is_active"] is False
        assert body["is_completed"] is False
        assert len(body["members"]) == 1

    def test_create_equb_requires_authentication(self, api_client):
        data = {
            "name": "unauthed_equb",
            "max_members": 2,
            "amount": "100.00",
            "cycle": "00:10:00",
        }
        response = api_client.post(reverse("equb-list"), data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("max_members", [1, 21])
    def test_create_equb_max_diallowed_max_members(self, max_members, make_authed_client):
        client = make_authed_client()
        data = {
                "name": "disallowed_max_members",
                    "max_members": max_members,
                    "amount": "100.00",
                    "cycle": "00:10:00",
                }
        response =client.post(reverse("equb-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "max_members" in response.json()

    def test_create_equb_cycle_below_minimum_rejected(self, make_authed_client):
        client = make_authed_client()
        data = {
            "name": "too_short_cycle",
            "max_members": 2,
            "amount": "100.00",
            "cycle": "00:00:30",  # below the 1-minute serializer minimum
        }
        response = client.post(reverse("equb-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRetrieveAndUpdateEqub:
    def test_member_can_retrieve_equb(self, make_authed_client):
        equb = EqubFactory()
        client = make_authed_client(equb.creator)
        response = client.get(reverse("equb-detail", args=[equb.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == equb.name

    def test_non_member_non_invitee_cannot_retrieve_equb(self, make_authed_client):
        """
        equbs should only be visible to:
            - members 
            - invitees 
            - friends of the equb creator (if the equb is public)
        """
        equb = EqubFactory()
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.get(reverse("equb-detail", args=[equb.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND


