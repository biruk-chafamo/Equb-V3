"""Serializer package, split by concept.

Re-exports every name the old flat ``serializers.py`` exposed so existing
``from .serializers import *`` and ``from .serializers import X`` sites keep
working unchanged.
"""
from .identity import (
    EditUserSerializer,
    FriendshipSerializer,
    GoogleAuthSerializer,
    ListUserSerializer,
    NestedUserSerializer,
    PaymentMethodSerializer,
    RegisterUserSerializer,
    WinnerUserSerializer,
)
from .equb import EqubSerializer, EqubSummarySerializer
from .bidding import BidSerializer
from .requests import (
    AcceptEqubInviteRequestSerializer,
    AcceptEqubJoinRequestSerializer,
    AcceptFriendRequestSerializer,
    EqubInviteRequestSerializer,
    EqubJoinRequestSerializer,
    FriendRequestSerializer,
)
from .payments import (
    AddressPaymentConfirmationRequestSerializer,
    ListPaymentConfirmationRequestSerializer,
    PaymentConfirmationRequestSerializer,
)

__all__ = [
    "AcceptEqubInviteRequestSerializer",
    "AcceptEqubJoinRequestSerializer",
    "AcceptFriendRequestSerializer",
    "AddressPaymentConfirmationRequestSerializer",
    "BidSerializer",
    "EditUserSerializer",
    "EqubInviteRequestSerializer",
    "EqubJoinRequestSerializer",
    "EqubSerializer",
    "EqubSummarySerializer",
    "FriendRequestSerializer",
    "FriendshipSerializer",
    "GoogleAuthSerializer",
    "ListPaymentConfirmationRequestSerializer",
    "ListUserSerializer",
    "NestedUserSerializer",
    "PaymentConfirmationRequestSerializer",
    "PaymentMethodSerializer",
    "RegisterUserSerializer",
    "WinnerUserSerializer",
]
