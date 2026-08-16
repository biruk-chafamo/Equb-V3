"""Uniqueness the application already assumes, now enforced by the database."""
from django.db import IntegrityError, transaction

import pytest

from moneypool.models import EqubMembership, Friendship, HighestBid
from moneypool.tests.factories import EqubFactory, UserFactory


@pytest.mark.django_db
class TestUniqueness:
    def test_a_member_cannot_be_added_to_the_same_equb_twice(self):
        user = UserFactory()
        equb = EqubFactory(creator=user, max_members=20)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                EqubMembership.objects.create(equb=equb, member=user)

    def test_a_friendship_cannot_be_recorded_twice_in_the_same_direction(self):
        a, b = UserFactory(), UserFactory()
        a.friends.add(b)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Friendship.objects.create(user=a, friend=b)

    def test_the_reverse_friendship_is_a_different_pair(self):
        a, b = UserFactory(), UserFactory()
        a.friends.add(b)

        assert Friendship.objects.filter(user=a, friend=b).exists()
        assert Friendship.objects.filter(user=b, friend=a).exists()

    def test_an_equb_round_cannot_have_two_highest_bids(self):
        equb = EqubFactory(creator=UserFactory(), max_members=20)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                HighestBid.objects.create(equb=equb, round=1)
