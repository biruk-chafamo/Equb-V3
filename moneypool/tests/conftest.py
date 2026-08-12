import pytest
from rest_framework.test import APIClient

from moneypool.adapters.django_notifier import DjangoNotifier
from moneypool.tests.factories import UserFactory
from moneypool.tests.fakes import RecordingLiveUpdates, RecordingScheduler


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def live_updates():
    return RecordingLiveUpdates()


@pytest.fixture
def scheduler():
    return RecordingScheduler()


@pytest.fixture
def notifier(live_updates, scheduler):
    return DjangoNotifier(live_updates=live_updates, scheduler=scheduler)


@pytest.fixture
def make_authed_client():
    def _make(user=None):
        client = APIClient()
        client.force_authenticate(user=user or UserFactory())
        return client

    return _make
