from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory, make_full_equb_via_add_member as _make_full_equb
from moneypool.services.equb_service import place_bid
from moneypool.tasks import select_winner_task


@pytest.mark.django_db
class TestRegisterUserBlankEmail:
    def test_blank_string_email_rejected(self, api_client):
        data = {
            "username": "blank_email_user",
            "first_name": "A",
            "last_name": "B",
            "email": "",
            "password": "a-Str0ng-password!",
            "password2": "a-Str0ng-password!",
        }
        response = api_client.post(reverse("user-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.json()
