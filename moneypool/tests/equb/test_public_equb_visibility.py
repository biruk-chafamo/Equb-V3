"""Whose equbs a user can see on a profile, and open."""
from django.urls import reverse
from rest_framework import status

import pytest

from moneypool.services.equb_service import add_member
from moneypool.tests.factories import EqubFactory, UserFactory


def _profile(client, owner):
    return client.get(reverse('equb-by-user'), {'user': owner.pk}).json()


@pytest.mark.django_db
class TestProfileVisibility:
    def test_a_non_friend_is_not_shown_the_owners_public_equbs(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=False)
        stranger = UserFactory()

        assert _profile(make_authed_client(stranger), equb.creator) == []

    def test_a_friend_of_the_creator_is_shown_them(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=False)
        friend = UserFactory()
        friend.friends.add(equb.creator)

        listed = _profile(make_authed_client(friend), equb.creator)

        assert [e['id'] for e in listed] == [equb.pk]

    def test_a_shared_equb_is_shown_without_friendship(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=True)
        viewer = UserFactory()
        add_member(equb, viewer)

        listed = _profile(make_authed_client(viewer), equb.creator)

        assert [e['id'] for e in listed] == [equb.pk]

    def test_a_private_equb_the_owner_joined_is_not_exposed(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=True)
        stranger = UserFactory()
        stranger.friends.add(equb.creator)

        assert _profile(make_authed_client(stranger), equb.creator) == []


@pytest.mark.django_db
class TestProfileNeverListsWhatItCannotOpen:
    def test_every_equb_a_profile_lists_can_be_opened(self, make_authed_client):
        owner = UserFactory()
        viewer = UserFactory()
        viewer.friends.add(owner)

        mine = EqubFactory(max_members=4, creator=owner, is_private=False)
        by_a_stranger = EqubFactory(max_members=4, is_private=False)
        add_member(by_a_stranger, owner)
        private = EqubFactory(max_members=4, creator=owner, is_private=True)
        shared = EqubFactory(max_members=4, creator=owner, is_private=True)
        add_member(shared, viewer)

        client = make_authed_client(viewer)
        listed = _profile(client, owner)
        listed_ids = {e['id'] for e in listed}

        assert listed_ids == {mine.pk, shared.pk}
        assert by_a_stranger.pk not in listed_ids
        assert private.pk not in listed_ids

        for equb_id in listed_ids:
            response = client.get(reverse('equb-detail', args=[equb_id]))
            assert response.status_code == status.HTTP_200_OK, equb_id


@pytest.mark.django_db
class TestRetrieveFollowsTheSameRule:
    def test_a_friend_can_open_a_public_equb(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=False)
        friend = UserFactory()
        friend.friends.add(equb.creator)

        response = make_authed_client(friend).get(reverse('equb-detail', args=[equb.pk]))

        assert response.status_code == status.HTTP_200_OK

    def test_a_stranger_cannot_open_a_public_equb(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=False)

        response = make_authed_client(UserFactory()).get(
            reverse('equb-detail', args=[equb.pk])
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_a_public_equb_by_a_friend_stays_out_of_the_home_feed(self, make_authed_client):
        equb = EqubFactory(max_members=3, is_private=False)
        friend = UserFactory()
        friend.friends.add(equb.creator)

        body = make_authed_client(friend).get(reverse('equb-list')).json()

        assert [e['id'] for e in body] == []
