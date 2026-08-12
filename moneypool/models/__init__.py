"""Model package.

Split by concept; this module re-exports every name the old flat ``models.py``
exposed, so ``from .models import *`` and ``from .models import X`` keep working
unchanged. Import order follows the dependency graph: identity has no internal
deps, equb needs identity, and so on.
"""
import datetime
import logging

from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from guardian.shortcuts import assign_perm
from rest_framework import serializers

from ..domain import settlement
from .identity import (
    Friendship,
    PaymentMethod,
    ServiceChoices,
    User,
    deleted_user,
)
from .equb import (
    BalanceManager,
    Equb,
    EqubMembership,
    Win,
)
from .bidding import (
    Bid,
    HighestBid,
)
from .requests import (
    EqubInviteRequest,
    EqubJoinRequest,
    FriendRequest,
    PaymentConfirmationRequest,
    Request,
    assign_notification_perm,
)
from .notifications import (
    NewEqubNotification,
    NewMemberNotification,
    NewPaymentConfirmationRequestNotification,
    NewRoundNotification,
    Notification,
    OutBidNotification,
)

__all__ = [
    "AbstractUser",
    "BalanceManager",
    "Bid",
    "Equb",
    "EqubInviteRequest",
    "EqubJoinRequest",
    "EqubMembership",
    "FriendRequest",
    "Friendship",
    "HighestBid",
    "MaxValueValidator",
    "MinValueValidator",
    "NewEqubNotification",
    "NewMemberNotification",
    "NewPaymentConfirmationRequestNotification",
    "NewRoundNotification",
    "Notification",
    "OutBidNotification",
    "PaymentConfirmationRequest",
    "PaymentMethod",
    "Request",
    "ServiceChoices",
    "User",
    "Win",
    "assign_notification_perm",
    "assign_perm",
    "datetime",
    "deleted_user",
    "logging",
    "models",
    "serializers",
    "settlement",
    "timezone",
    "transaction",
]
