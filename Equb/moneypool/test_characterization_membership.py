from django.urls import reverse
from rest_framework import status

import pytest

from .models import EqubJoinRequest
from .services.equb_service import add_member
from .factories import UserFactory, EqubFactory, EqubInviteRequestFactory, EqubJoinRequestFactory

@pytest.mark.django_db
class TestEqubInviteRequest:
    def test_member_can_invite_non_member(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        client = make_authed_client(equb.creator)
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "receiver": reverse("user-detail", args=[invitee.pk]),
        }
        response = client.post(reverse("equbinviterequest-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

