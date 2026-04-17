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

    def test_non_member_cannot_invite(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        outsider = UserFactory()
        invitee = UserFactory()
        client = make_authed_client(outsider)
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "receiver": reverse("user-detail", args=[invitee.pk]),
        }
        response = client.post(reverse("equbinviterequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "sender" in response.json()

    def test_cannot_invite_self(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        client = make_authed_client(equb.creator)
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "receiver": reverse("user-detail", args=[equb.creator.pk]),
        }
        response = client.post(reverse("equbinviterequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()
        
    def test_cannot_invite_existing_member(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        add_member(equb, invitee)
        client = make_authed_client(equb.creator)
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "receiver": reverse("user-detail", args=[invitee.pk]),
        }
        response = client.post(reverse("equbinviterequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()

    def test_duplicate_pending_invite_rejected(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        client = make_authed_client(equb.creator)
        data = {
            "equb": reverse("equb-detail", args=[equb.pk]),
            "receiver": reverse("user-detail", args=[invitee.pk]),
        }
        response = client.post(reverse("equbinviterequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()

    def test_accept_invite_adds_member(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        invite = EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        client = make_authed_client(invitee)
        response = client.patch(
            reverse("equbinviterequest-detail", args=[invite.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_200_OK
        equb.refresh_from_db()
        assert invitee in equb.members.all()

    def test_reject_invite_does_not_add_member(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        invite = EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        client = make_authed_client(invitee)
        response = client.patch(
            reverse("equbinviterequest-detail", args=[invite.pk]), {"is_rejected": True}
        )
        assert response.status_code == status.HTTP_200_OK
        equb.refresh_from_db()
        assert invitee not in equb.members.all()

    def test_receiver_can_accept_invite(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        invite = EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        client = make_authed_client(invitee)
        response = client.patch(
            reverse("equbinviterequest-detail", args=[invite.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_sender_cannot_accept_invite(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        invite = EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        client = make_authed_client(equb.creator)
        response = client.patch(
            reverse("equbinviterequest-detail", args=[invite.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_outsider_cannot_accept_invite(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        invitee = UserFactory()
        invite = EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        outsider = UserFactory()
        client = make_authed_client(outsider)
        response = client.patch(
            reverse("equbinviterequest-detail", args=[invite.pk]), {"is_accepted": True}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_full_equb_activates_once_max_members_reached(self, make_authed_client):
        equb = EqubFactory(max_members=2)
        invitee = UserFactory()
        invite = EqubInviteRequestFactory(equb=equb, receiver=invitee, sender=equb.creator)
        client = make_authed_client(invitee)
        client.patch(
            reverse("equbinviterequest-detail", args=[invite.pk]), {"is_accepted": True}
        )
        equb.refresh_from_db()
        assert equb.is_active is True
        assert equb.balance_manager.finished_rounds == 0
        assert equb.balance_manager.start_date is not None

    def test_consensus_required_for_sending_invite_request(self, make_authed_client):
        #TODO: implement feature
        pass
        

@pytest.mark.django_db
class TestEqubJoinRequest:
    def test_non_member_can_request_to_join(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        requester = UserFactory()
        client = make_authed_client(requester)
        data = {"equb": reverse("equb-detail", args=[equb.pk])}
        response = client.post(reverse("equbjoinrequest-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

    def test_existing_member_cannot_request_to_join(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        client = make_authed_client(equb.creator)
        data = {"equb": reverse("equb-detail", args=[equb.pk])}
        response = client.post(reverse("equbjoinrequest-list"), data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "receiver" in response.json()

    def test_join_request_receiver_defaults_to_equb_creator(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        requester = UserFactory()
        client = make_authed_client(requester)
        data = {"equb": reverse("equb-detail", args=[equb.pk])}
        response = client.post(reverse("equbjoinrequest-list"), data)
        assert response.status_code == status.HTTP_201_CREATED

        join_request = EqubJoinRequest.objects.get(pk=response.data["id"])
        assert join_request.receiver == equb.creator

    def test_creator_accepting_join_request_adds_member(self, make_authed_client):
        equb = EqubFactory(max_members=3)
        requester = UserFactory()
        join_request = EqubJoinRequestFactory(
            equb=equb, sender=requester, receiver=equb.creator
        )
        client = make_authed_client(equb.creator)
        response = client.patch(
            reverse("equbjoinrequest-detail", args=[join_request.pk]),
            {"is_accepted": True},
        )
        assert response.status_code == status.HTTP_200_OK
        equb.refresh_from_db()
        assert requester in equb.members.all()

    def test_full_equb_activates_once_max_members_reached(self, make_authed_client):
        equb = EqubFactory(max_members=2)
        requester = UserFactory()
        join_request = EqubJoinRequestFactory(
            equb=equb, sender=requester, receiver=equb.creator
        )
        client = make_authed_client(equb.creator)
        client.patch(
            reverse("equbjoinrequest-detail", args=[join_request.pk]),
            {"is_accepted": True},
        )
        equb.refresh_from_db()
        assert equb.is_active is True
        assert equb.balance_manager.finished_rounds == 0
        assert equb.balance_manager.start_date is not None


