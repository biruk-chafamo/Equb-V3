from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from .factories import EqubFactory, UserFactory, make_full_equb_via_add_member as _make_full_equb
from .services.equb_service import place_bid
from .tasks import select_winner_task


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


@pytest.mark.django_db
class TestBidValidationRemainingBranches:
    def test_cannot_bid_again_after_already_winning(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        winner = members[0]
        place_bid(winner, equb, Decimal("0.900"))
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        assert equb.balance_manager.latest_winner() == winner

        client = make_authed_client(winner)
        response = client.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.500"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "user" in response.json()

