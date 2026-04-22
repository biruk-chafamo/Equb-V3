from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from .factories import UserFactory, BidFactory, make_full_equb_via_join_requests as _make_full_equb
from .models import HighestBid, OutBidNotification
from .tasks import select_winner_task


@pytest.mark.django_db
class TestPlaceBid:
    def test_bid_above_max_rejected(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        client = make_authed_client(members[0])
        data = {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "1.500"}
        response = client.post(reverse("bid-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bid_of_zero_rejected(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        client = make_authed_client(members[0])
        data = {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.000"}
        response = client.post(reverse("bid-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

