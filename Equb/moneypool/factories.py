import factory
from factory.django import DjangoModelFactory
from decimal import Decimal
import datetime

from .models import (
    User,
    PaymentMethod,
    ServiceChoices,
    Equb,
    Bid,
    FriendRequest,
    EqubJoinRequest,
    EqubInviteRequest,
    PaymentConfirmationRequest,
)
from .services.equb_service import add_member


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"test_user_{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}")
    bank_account = Decimal("0.00")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "test_password")
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, password=password, **kwargs)


