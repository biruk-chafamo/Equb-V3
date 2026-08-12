import warnings

import pytest
from django.core.paginator import UnorderedObjectListWarning
from django.urls import reverse
from rest_framework import status

from moneypool.tests.factories import UserFactory


def _search(client, name):
    return client.get(reverse("user-search"), {"name": name})


@pytest.mark.django_db
class TestUserSearch:
    def test_requires_a_name(self, make_authed_client):
        response = make_authed_client().get(reverse("user-search"))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_matches_on_username_first_name_and_last_name(self, make_authed_client):
        UserFactory(username="zebra", first_name="Alice", last_name="Zulu")
        client = make_authed_client(UserFactory(username="searcher"))

        for term in ("zebra", "Alice", "Zulu"):
            usernames = [u["username"] for u in _search(client, term).data["results"]]
            assert "zebra" in usernames

    def test_excludes_the_searching_user(self, make_authed_client):
        user = UserFactory(username="findme_self")
        client = make_authed_client(user)

        usernames = [u["username"] for u in _search(client, "findme").data["results"]]
        assert "findme_self" not in usernames

    def test_results_are_ordered_by_id(self, make_authed_client):
        for i in range(8):
            UserFactory(username=f"ordered_{i}")
        client = make_authed_client(UserFactory(username="searcher_ordered"))

        ids = [u["id"] for u in _search(client, "ordered_").data["results"]]

        assert ids == sorted(ids)

    def test_pagination_does_not_warn_about_an_unordered_queryset(
        self, make_authed_client
    ):
        for i in range(8):
            UserFactory(username=f"warned_{i}")
        client = make_authed_client(UserFactory(username="searcher_warned"))

        with warnings.catch_warnings():
            warnings.simplefilter("error", UnorderedObjectListWarning)
            assert _search(client, "warned_").status_code == status.HTTP_200_OK

    def test_pages_do_not_overlap(self, make_authed_client):
        for i in range(8):
            UserFactory(username=f"paged_{i}")
        client = make_authed_client(UserFactory(username="searcher_paged"))

        first = _search(client, "paged_").data
        second = client.get(
            reverse("user-search"), {"name": "paged_", "page": 2}
        ).data

        first_ids = {u["id"] for u in first["results"]}
        second_ids = {u["id"] for u in second["results"]}

        assert first["count"] == 8
        assert len(first_ids) == 5
        assert first_ids.isdisjoint(second_ids)
