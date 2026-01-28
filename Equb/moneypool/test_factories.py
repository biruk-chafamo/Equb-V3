import pytest

from .factories import (
    UserFactory,
    PaymentMethodFactory,
    EqubFactory,
    BidFactory,
    FriendRequestFactory,
    EqubJoinRequestFactory,
    EqubInviteRequestFactory,
    PaymentConfirmationRequestFactory,
)


@pytest.mark.django_db
def test_user_factory_creates_usable_login():
    user = UserFactory(username="factory_login_user", password="a-real-password")
    assert user.check_password("a-real-password")
    # signals.py::new_user auto-creates a default Cash payment method
    assert user.selected_payment_methods.count() == 1


@pytest.mark.django_db
def test_payment_method_factory():
    pm = PaymentMethodFactory()
    assert pm.user_id is not None


