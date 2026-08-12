from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.tests.factories import EqubFactory, EqubJoinRequestFactory, FriendRequestFactory, UserFactory
from moneypool.services.equb_service import add_member, place_bid
from moneypool.tasks import select_winner_task
from decimal import Decimal


@pytest.mark.django_db
class TestPaymentConfirmationRequestPermissions:
    def test_only_receiver_can_accept(self, make_authed_client):
        equb = EqubFactory(max_members=2)
        loser = UserFactory()
        add_member(equb, loser)
        equb.refresh_from_db()
        winner = equb.creator
        place_bid(winner, equb, Decimal("0.900"))
        select_winner_task.now(equb.name)

        pm = loser.selected_payment_methods.first()
        loser_client = make_authed_client(loser)
        create_response = loser_client.post(
            reverse("paymentconfirmationrequest-list"),
            {
                "equb": reverse("equb-detail", args=[equb.pk]),
                "round": 1,
                "payment_method": reverse("paymentmethod-detail", args=[pm.pk]),
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        outsider = UserFactory()
        outsider_client = make_authed_client(outsider)
        response = outsider_client.patch(create_response.data["url"], {"is_accepted": True})
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # the sender themselves also can't accept their own request, only
        # the receiver (winner) has the change permission assigned
        response = loser_client.patch(create_response.data["url"], {"is_accepted": True})
        assert response.status_code == status.HTTP_403_FORBIDDEN
