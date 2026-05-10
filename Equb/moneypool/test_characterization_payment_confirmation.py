from decimal import Decimal

from django.urls import reverse
from rest_framework import status

import pytest

from .factories import (
    PaymentMethodFactory,
    UserFactory,
    make_full_equb_via_join_requests as _make_full_equb,
)
from .models import PaymentConfirmationRequest, ServiceChoices, Win, User
from .tasks import select_winner_task


@pytest.mark.django_db
class TestPaymentConfirmationLifecycle:
    def test_full_two_round_lifecycle_bank_accounts(self, make_authed_client):
        equb, (user0, user1) = _make_full_equb(max_members=2, amount=Decimal("100.00"))

        # round 1: user0 bids and wins
        client0 = make_authed_client(user0)
        client0.post(
            reverse("bid-list"),
            {"equb": reverse("equb-detail", args=[equb.pk]), "amount": "0.900"},
        )
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        assert equb.balance_manager.latest_winner() == user0
        
        # user1 sends a payment confirmation request to user0
        client1 = make_authed_client(user1)
        selected_payment_method_1 = user1.selected_payment_methods.filter(
            service=ServiceChoices.CASH
        ).first()
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "round": 1,
            "payment_method": reverse("paymentmethod-detail", args=[selected_payment_method_1.pk]),
        }
        response = client1.post(reverse("paymentconfirmationrequest-list"), data)
        assert response.status_code == status.HTTP_201_CREATED
        expected_deduction = equb.balance_manager.calculate_losers_deductions(member=user1, round=1)
        assert PaymentConfirmationRequest.objects.get(equb=equb, sender=user1).amount == expected_deduction

        client0.patch(response.data["url"], {"is_accepted": True}) # this initiates round 2

        # round 2
        select_winner_task.now(equb.name)
        equb.refresh_from_db()
        assert equb.balance_manager.latest_winner() == user1

        # user0 sends payment confirmation to the winner (user1)
        selected_payment_method_0 = user0.selected_payment_methods.filter(
            service=ServiceChoices.CASH
        ).first()
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "round": 2,
            "payment_method": reverse("paymentmethod-detail", args=[selected_payment_method_0.pk]),
        }
        response = client0.post(reverse("paymentconfirmationrequest-list"), data)
        assert response.status_code == status.HTTP_201_CREATED
        expected_deduction_2 = equb.balance_manager.calculate_losers_deductions(member=user0, round=2)
        assert PaymentConfirmationRequest.objects.get(equb=equb, sender=user0).amount == expected_deduction_2

        # accepting completes the equb
        client1.patch(response.data["url"], {"is_accepted": True})
        equb.refresh_from_db()
        assert equb.balance_manager.finished_rounds == 2
        assert equb.is_completed is True

