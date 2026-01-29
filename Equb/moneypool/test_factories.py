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


@pytest.mark.django_db
def test_equb_factory_triggers_balance_manager_and_highest_bid():
    equb = EqubFactory()
    # signals.py::new_equb_action auto-creates these on Equb creation
    assert equb.balance_manager is not None
    assert equb.highest_bids.get(round=1) is not None
    # signals.py::set_creator_membership adds creator as a member
    assert equb.creator in equb.members.all()


