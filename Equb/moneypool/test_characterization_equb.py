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

