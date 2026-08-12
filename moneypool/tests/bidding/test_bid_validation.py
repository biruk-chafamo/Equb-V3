from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory, make_full_equb_via_add_member as _make_full_equb
from moneypool.services.equb_service import place_bid
from moneypool.tasks import select_winner_task


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

    def test_cannot_bid_before_equb_is_active(self, make_authed_client):
        # max_members=3, only the creator has joined, equb isn't full/active yet
        equb = EqubFactory(max_members=3)
        assert equb.is_active is False
        client = make_authed_client(equb.creator)
        response = client.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.500"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "equb" in response.json()

    def test_cannot_bid_during_payment_stage(self, make_authed_client):
        equb, members = _make_full_equb(max_members=3)
        place_bid(members[0], equb, Decimal("0.900"))
        select_winner_task.now(equb.name)  # members[0] wins, equb enters payment stage
        equb.refresh_from_db()
        assert equb.is_in_payment_stage is True

        # members[1] hasn't won, would otherwise be a valid bidder, except
        # the equb is now in the payment stage for the round already decided
        client = make_authed_client(members[1])
        response = client.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.500"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "equb" in response.json()

    def test_cannot_bid_in_the_final_round(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        place_bid(members[0], equb, Decimal("0.900"))
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        equb.balance_manager.setup_next_round()
        equb.refresh_from_db()
        assert equb.balance_manager.current_round() == equb.max_members  # final round

        client = make_authed_client(members[1])
        response = client.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.500"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "equb" in response.json()
