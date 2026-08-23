"""How the cost of serving an equb grows."""
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

import pytest

from moneypool.tests.factories import UserFactory, make_full_equb_via_add_member

MAX_QUERIES_PER_MEMBER = 0.1
MAX_QUERIES_PER_EQUB = 2.0
MAX_BYTES_PER_MEMBER = 150


def _cost(client, url):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
        assert response.status_code == 200, response.status_code
        return len(ctx), len(response.content)


def _equb_of(make_authed_client, members):
    equb, users = make_full_equb_via_add_member(members)
    return equb, make_authed_client(users[0])


@pytest.mark.parametrize('endpoint', ['detail', 'list'])
@pytest.mark.django_db
class TestCostPerMember:
    def _measure(self, make_authed_client, endpoint, members):
        equb, client = _equb_of(make_authed_client, members)
        url = (reverse('equb-detail', args=[equb.pk]) if endpoint == 'detail'
               else reverse('equb-list'))
        return _cost(client, url)

    def test_queries_are_flat_in_member_count(self, make_authed_client, endpoint):
        small_q, _ = self._measure(make_authed_client, endpoint, 3)
        large_q, _ = self._measure(make_authed_client, endpoint, 20)

        per_member = (large_q - small_q) / 17
        assert per_member <= MAX_QUERIES_PER_MEMBER, (
            f'{endpoint}: {small_q} queries at 3 members, {large_q} at 20 '
            f'({per_member:.2f} per extra member)'
        )

    def test_each_member_costs_one_nested_user_of_bytes(self, make_authed_client, endpoint):
        _, small_b = self._measure(make_authed_client, endpoint, 3)
        _, large_b = self._measure(make_authed_client, endpoint, 20)

        per_member = (large_b - small_b) / 17
        assert per_member <= MAX_BYTES_PER_MEMBER, (
            f'{endpoint}: {small_b} bytes at 3 members, {large_b} at 20 '
            f'({per_member:.0f} per extra member) - a member is being '
            f'serialized more than once'
        )


@pytest.mark.django_db
class TestCostPerEqubInAFeed:
    def _measure(self, make_authed_client, equbs):
        user = UserFactory()
        for _ in range(equbs):
            equb, _members = make_full_equb_via_add_member(4)
            equb.members.add(user)
        return _cost(make_authed_client(user), reverse('equb-list'))

    def test_queries_grow_by_at_most_one_per_equb(self, make_authed_client):
        few_q, _ = self._measure(make_authed_client, 1)
        many_q, _ = self._measure(make_authed_client, 6)

        per_equb = (many_q - few_q) / 5
        assert per_equb <= MAX_QUERIES_PER_EQUB, (
            f'{few_q} queries for 1 equb, {many_q} for 6 '
            f'({per_equb:.1f} per extra equb)'
        )


@pytest.mark.django_db
class TestJoinRequestListingCost:
    def _measure(self, make_authed_client, members):
        from moneypool.tests.factories import EqubJoinRequestFactory, make_forming_equb

        equb, joined = make_forming_equb(members + 1, members)
        requester = UserFactory()
        joined[0].friends.add(requester)
        EqubJoinRequestFactory(equb=equb, sender=requester, receiver=equb.creator)
        client = make_authed_client(joined[0])
        return _cost(client, reverse('equbjoinrequest-by-equb') + f'?equb={equb.pk}')

    def test_queries_are_flat_in_member_count(self, make_authed_client):
        small_q, _ = self._measure(make_authed_client, 3)
        large_q, _ = self._measure(make_authed_client, 20)

        per_member = (large_q - small_q) / 17
        assert per_member <= MAX_QUERIES_PER_MEMBER, (
            f'{small_q} queries at 3 members, {large_q} at 20 '
            f'({per_member:.2f} per extra member)'
        )
