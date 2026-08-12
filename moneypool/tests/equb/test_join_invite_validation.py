from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory, make_full_equb_via_add_member as _make_full_equb
from moneypool.services.equb_service import place_bid
from moneypool.tasks import select_winner_task


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
