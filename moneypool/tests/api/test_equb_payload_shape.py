"""What each equb context puts on the wire."""
from django.urls import reverse

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory

NESTED_USER_FIELDS = {'id', 'first_name', 'last_name', 'score', 'profile_picture'}

SUMMARY_FIELDS = {
    'id', 'name', 'amount', 'max_members', 'cycle', 'creation_date',
    'is_private', 'is_active', 'is_completed', 'is_in_payment_stage',
    'current_round', 'current_award', 'current_highest_bid',
    'percent_joined', 'percent_completed', 'is_won_by_user',
    'user_payment_status', 'current_user_is_member',
    'time_left_till_next_round', 'latest_winner', 'members', 'creator_id',
}

DETAIL_ONLY_FIELDS = {
    'url', 'end_date', 'current_highest_bidder_id', 'payment_collection_dates',
    'is_created_by_user', 'confirmed_payer_ids', 'unconfirmed_payer_ids',
    'unpaid_member_ids', 'rejected_payer_ids',
}


@pytest.fixture
def equb_and_client(make_authed_client):
    user = UserFactory()
    equb = EqubFactory(creator=user, max_members=20)
    return equb, make_authed_client(user)


@pytest.mark.django_db
class TestEqubShape:
    def test_a_feed_row_carries_only_what_a_card_renders(self, equb_and_client):
        _, client = equb_and_client

        body = client.get(reverse('equb-list')).json()

        assert set(body[0]) == SUMMARY_FIELDS

    def test_the_detail_adds_the_rest(self, equb_and_client):
        equb, client = equb_and_client

        body = client.get(reverse('equb-detail', args=[equb.pk])).json()

        assert set(body) == SUMMARY_FIELDS | DETAIL_ONLY_FIELDS

    def test_creating_returns_the_full_detail(self, make_authed_client):
        client = make_authed_client()

        body = client.post(reverse('equb-list'), {
            'name': 'shape_check', 'max_members': 3,
            'amount': '100.00', 'cycle': '00:10:00', 'is_private': False,
        }).json()

        assert set(body) == SUMMARY_FIELDS | DETAIL_ONLY_FIELDS


@pytest.mark.django_db
class TestUserIsSentOncePerResponse:
    def test_members_carry_the_nested_shape(self, equb_and_client):
        equb, client = equb_and_client

        body = client.get(reverse('equb-detail', args=[equb.pk])).json()

        assert set(body['members'][0]) == NESTED_USER_FIELDS

    def test_every_user_an_equb_names_is_an_id(self, equb_and_client):
        equb, client = equb_and_client

        body = client.get(reverse('equb-detail', args=[equb.pk])).json()

        for key in ['creator_id', 'current_highest_bidder_id']:
            assert body[key] is None or isinstance(body[key], int)
        for key in ['unpaid_member_ids', 'confirmed_payer_ids',
                    'unconfirmed_payer_ids', 'rejected_payer_ids']:
            assert all(isinstance(i, int) for i in body[key])

    def test_those_ids_resolve_against_members(self, equb_and_client):
        equb, client = equb_and_client
        equb.members.add(UserFactory())

        body = client.get(reverse('equb-detail', args=[equb.pk])).json()
        member_ids = {m['id'] for m in body['members']}

        referenced = list(body['unpaid_member_ids'])
        if body['creator_id'] is not None:
            referenced.append(body['creator_id'])

        assert referenced
        assert set(referenced) <= member_ids

    def test_an_invite_nests_the_summary_not_the_whole_equb(self, make_authed_client):
        sender = UserFactory()
        equb = EqubFactory(creator=sender, max_members=20)
        client = make_authed_client(sender)

        client.post(reverse('equbinviterequest-list'), {
            'equb': reverse('equb-detail', args=[equb.pk]),
            'receiver': reverse('user-detail', args=[UserFactory().pk]),
        })
        body = client.get(reverse('equbinviterequest-list')).json()['results']

        assert set(body[0]['equb']) == SUMMARY_FIELDS
