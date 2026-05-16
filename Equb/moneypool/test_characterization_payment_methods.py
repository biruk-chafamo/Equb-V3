
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

