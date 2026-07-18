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


@pytest.mark.django_db
class TestEqubJoinRequestCannotJoinActiveEqub:
    def test_cannot_request_to_join_an_already_active_equb(self, make_authed_client):
        equb, _ = _make_full_equb(max_members=2)
        assert equb.is_active is True
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.post(
            reverse("equbjoinrequest-list"), {"equb": reverse("equb-detail", args=[equb.pk])}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "equb" in response.json()


@pytest.mark.django_db
class TestEqubInviteRequestCannotInviteToActiveEqub:
    def test_cannot_invite_to_an_already_active_equb(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        assert equb.is_active is True
        new_user = UserFactory()
        client = make_authed_client(members[0])
        response = client.post(
            reverse("equbinviterequest-list"),
            {
                "equb": reverse("equb-detail", args=[equb.pk]),
                "receiver": reverse("user-detail", args=[new_user.pk]),
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "equb" in response.json()


