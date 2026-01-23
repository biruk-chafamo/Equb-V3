import pytest
from rest_framework.test import APIClient

from .adapters.django_notifier import DjangoNotifier
from .factories import UserFactory
from .fakes import RecordingLiveUpdates, RecordingScheduler


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


