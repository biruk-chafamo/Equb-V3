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


