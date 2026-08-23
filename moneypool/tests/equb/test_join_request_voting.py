from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.domain.approval import CREATOR_ONLY, UNANIMOUS
from moneypool.models import EqubJoinRequestVote
from moneypool.tests.factories import (
    EqubJoinRequestFactory,
    UserFactory,
    make_forming_equb,
)


def _vote(client, join_request, approve):
    return client.post(
        reverse("equbjoinrequest-vote", args=[join_request.pk]), {"approve": approve}, format="json"
    )


@pytest.fixture
def forming():
    """A 5 member equb with 4 already in it, and an outsider asking to join."""
    def _make(max_members=5, members=4, policy=None):
        equb, joined = make_forming_equb(max_members, members)
        if policy is not None:
            equb.join_approval_policy = policy
            equb.save()
        requester = UserFactory()
        join_request = EqubJoinRequestFactory(equb=equb, sender=requester, receiver=equb.creator)
        return equb, joined, requester, join_request
    return _make


@pytest.mark.django_db
class TestCreatorDecides:
    def test_creator_approving_adds_the_member_at_once(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()

        response = _vote(make_authed_client(equb.creator), join_request, True)

        assert response.status_code == status.HTTP_200_OK
        join_request.refresh_from_db()
        assert join_request.is_accepted is True
        assert equb.members.filter(pk=requester.pk).exists()

    def test_creator_declining_rejects_at_once(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()

        _vote(make_authed_client(equb.creator), join_request, False)

        join_request.refresh_from_db()
        assert join_request.is_rejected is True
        assert not equb.members.filter(pk=requester.pk).exists()


@pytest.mark.django_db
class TestMajorityDecides:
    def test_one_short_of_a_majority_does_not_add_the_member(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()
        members = [m for m in joined if m != equb.creator]

        for member in members[:2]:
            _vote(make_authed_client(member), join_request, True)

        join_request.refresh_from_db()
        assert join_request.is_accepted is False
        assert not equb.members.filter(pk=requester.pk).exists()

    def test_a_majority_adds_the_member(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()
        members = [m for m in joined if m != equb.creator]

        for member in members:
            _vote(make_authed_client(member), join_request, True)

        join_request.refresh_from_db()
        assert join_request.is_accepted is True
        assert equb.members.filter(pk=requester.pk).exists()

    def test_enough_declines_to_put_a_majority_out_of_reach_rejects(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()
        members = [m for m in joined if m != equb.creator]

        for member in members:
            response = _vote(make_authed_client(member), join_request, False)
            if response.status_code != status.HTTP_200_OK:
                break

        join_request.refresh_from_db()
        assert join_request.is_rejected is True
        assert not equb.members.filter(pk=requester.pk).exists()

    def test_changing_your_mind_replaces_your_vote(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()
        member = next(m for m in joined if m != equb.creator)
        client = make_authed_client(member)

        _vote(client, join_request, True)
        _vote(client, join_request, False)

        votes = EqubJoinRequestVote.objects.filter(request=join_request, voter=member)
        assert votes.count() == 1
        assert votes.first().approve is False


@pytest.mark.django_db
class TestOtherPolicies:
    def test_unanimous_needs_every_member(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming(policy=UNANIMOUS)

        members = [m for m in joined if m != equb.creator]

        for member in members:
            _vote(make_authed_client(member), join_request, True)
        join_request.refresh_from_db()
        assert join_request.is_accepted is False

    def test_creator_only_ignores_member_votes(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming(policy=CREATOR_ONLY)
        members = [m for m in joined if m != equb.creator]

        for member in members:
            _vote(make_authed_client(member), join_request, True)

        join_request.refresh_from_db()
        assert join_request.is_accepted is False
        assert not equb.members.filter(pk=requester.pk).exists()


@pytest.mark.django_db
class TestVotingIsClosed:
    def test_cannot_vote_on_a_decided_request(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming()
        _vote(make_authed_client(equb.creator), join_request, True)

        member = next(m for m in joined if m != equb.creator)
        response = _vote(make_authed_client(member), join_request, True)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_vote_once_the_equb_has_filled(self, make_authed_client, forming):
        equb, joined, requester, join_request = forming(max_members=3, members=2)
        from moneypool.services.equb_service import add_member

        add_member(equb, UserFactory())
        equb.refresh_from_db()
        assert equb.is_active is True

        response = _vote(make_authed_client(equb.creator), join_request, True)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
