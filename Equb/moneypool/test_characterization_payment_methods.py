
from django.urls import reverse
from rest_framework import status

import pytest

from .factories import UserFactory, PaymentMethodFactory
from .models import ServiceChoices


@pytest.mark.django_db
class TestPaymentMethod:
    def test_default_cash_payment_creation(self):
        user = UserFactory(username="new_user")
        assert user.selected_payment_methods.count() == 1

    def test_create_payment_method(self, make_authed_client):
        client = make_authed_client()
        data = {"service": ServiceChoices.VENMO, "detail": "@my-venmo"}
        response = client.post(reverse("paymentmethod-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_returns_only_own_payment_methods(self, make_authed_client):
        user = UserFactory()
        other = UserFactory()
        PaymentMethodFactory(user=user, service=ServiceChoices.VENMO)
        PaymentMethodFactory(user=other, service=ServiceChoices.PAYPAL)
        client = make_authed_client(user)
        response = client.get(reverse("paymentmethod-list"))
        assert response.status_code == status.HTTP_200_OK
        user_services = [pm["service"] for pm in response.json()]
        assert len(user_services) == 2
        assert "PayPal" not in user_services
        assert "Venmo" in user_services
        assert "Cash" in user_services

    @pytest.mark.xfail(reason="Deleting payment method is not yet implemented")
    def test_deleting_own_payment_method_is_allowed(self, make_authed_client):
        user = UserFactory()
        pm = PaymentMethodFactory(user=user, service=ServiceChoices.ZELLE)
        client = make_authed_client(user)
        response = client.delete(reverse("paymentmethod-detail", args=[pm.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_duplicate_payment_method_rejected(self, make_authed_client):
        user = UserFactory()
        PaymentMethodFactory(user=user, service=ServiceChoices.VENMO, detail="@dup")
        client = make_authed_client(user)
        data = {"service": ServiceChoices.VENMO, "detail": "@dup"}
        response = client.post(reverse("paymentmethod-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_services_action_lists_all_choices(self, make_authed_client):
        client = make_authed_client()
        response = client.get(reverse("paymentmethod-services"))
        assert response.status_code == status.HTTP_200_OK
        assert set(response.json()) == {c[0] for c in ServiceChoices.choices}
