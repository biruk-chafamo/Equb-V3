"""View package, split by concept.

Re-exports every name the old flat ``views.py`` exposed so ``urls.py``'s
``from . import views`` and any ``from .views import X`` keep working.
"""
from .identity import (
    AuthPlatform,
    UserViewSet,
    check_signin_method,
    google_auth,
    smart_password_reset,
)
from .equb import EqubViewSet
from .bidding import BidViewSet
from .requests import (
    EqubInviteRequestViewSet,
    EqubJoinRequestViewSet,
    FriendRequestViewSet,
)
from .payments import (
    PaymentConfirmationRequestViewSet,
    PaymentMethodViewSet,
)

__all__ = [
    "AuthPlatform",
    "BidViewSet",
    "EqubInviteRequestViewSet",
    "EqubJoinRequestViewSet",
    "EqubViewSet",
    "FriendRequestViewSet",
    "PaymentConfirmationRequestViewSet",
    "PaymentMethodViewSet",
    "UserViewSet",
    "check_signin_method",
    "google_auth",
    "smart_password_reset",
]
