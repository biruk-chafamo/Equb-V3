import datetime
from decimal import Decimal

import pytest

from .django_notifier import DjangoNotifier
from ..factories import (
    BidFactory,
    EqubFactory,
    PaymentConfirmationRequestFactory,
    UserFactory,
)
from ..fakes import FixedClock, RecordingLiveUpdates, RecordingScheduler
from ..models import (
    NewEqubNotification,
    NewMemberNotification,
    NewPaymentConfirmationRequestNotification,
    NewRoundNotification,
    OutBidNotification,
)

FIXED_NOW = datetime.datetime(2025, 1, 1, 12, 0, tzinfo=datetime.timezone.utc)


@pytest.fixture
def live_updates():
    return RecordingLiveUpdates()


@pytest.fixture
def scheduler():
    return RecordingScheduler()


@pytest.fixture
def notifier(live_updates, scheduler):
    return DjangoNotifier(
        clock=FixedClock(FIXED_NOW), live_updates=live_updates, scheduler=scheduler
    )


