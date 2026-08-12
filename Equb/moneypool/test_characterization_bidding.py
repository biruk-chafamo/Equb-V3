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

    def test_outbidding_updates_highest_bid(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        client_a = make_authed_client(members[0])
        client_b = make_authed_client(members[1])

        client_a.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.100"},
        )
        response = client_b.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.200"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert HighestBid.objects.get(equb=equb, round=1).bid.amount == Decimal("0.200")
        assert OutBidNotification.objects.filter(equb=equb).count() == 2 * len(members)

    def test_lower_bid_does_not_become_highest(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        client_a = make_authed_client(members[0])
        client_b = make_authed_client(members[1])

        client_a.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.500"},
        )
        response = client_b.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.100"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        # highest bid is unchanged, still member[0]'s 0.500
        assert HighestBid.objects.get(equb=equb, round=1).bid.amount == Decimal("0.500")


@pytest.mark.django_db
class TestWinnerSelection:
    def test_highest_bidder_wins_round(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        client_a = make_authed_client(members[0])
        client_b = make_authed_client(members[1])

        client_a.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.100"},
        )
        client_b.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.900"},
        )

        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        assert equb.balance_manager.received.all()[0] == members[1]
        assert equb.is_in_payment_stage is True

    def test_no_bid_still_selects_a_winner(self):
        equb, members = _make_full_equb(max_members=2)
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        winner = equb.balance_manager.received.all()[0]
        assert winner in members


@pytest.mark.django_db
class TestBidPermissions:
    def test_member_can_place_bid(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        bidder = members[0]
        client = make_authed_client(bidder)
        data = {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.100"}
        response = client.post(reverse("bid-list"), data)

        assert response.status_code == status.HTTP_201_CREATED
        assert HighestBid.objects.get(equb=equb, round=1).bid.amount == Decimal("0.100")
        # every member gets an OutBidNotification when a new highest bid lands
        assert OutBidNotification.objects.filter(equb=equb).count() == len(members)

    def test_non_member_cannot_bid(self, make_authed_client):
        equb, _ = _make_full_equb(max_members=2)
        outsider = UserFactory()
        client = make_authed_client(outsider)
        data = {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.100"}
        response = client.post(reverse("bid-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "user" in response.json()
    def test_outsider_cannot_list_bids_for_equb_they_are_not_in(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        BidFactory(equb=equb, user=members[0], amount="0.100", round=1)
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.get(reverse("bid-list"))
        assert response.status_code == status.HTTP_200_OK
        # get_queryset() filters to equbs the user has joined
        assert response.json() == []

    def test_outsider_cannot_delete_a_bid(self, make_authed_client):
        equb, members = _make_full_equb(max_members=2)
        bid = BidFactory(equb=equb, user=members[0], amount="0.100", round=1)
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.delete(reverse("bid-detail", args=[bid.pk]))
        assert response.status_code == status.HTTP_403_FORBIDDEN
