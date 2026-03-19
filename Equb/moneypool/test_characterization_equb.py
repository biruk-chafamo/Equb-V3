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

