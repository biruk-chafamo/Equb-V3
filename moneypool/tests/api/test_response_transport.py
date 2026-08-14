"""How responses leave the server: compression and content type."""
import gzip

from django.urls import reverse

import pytest

from moneypool.tests.factories import EqubFactory, UserFactory


@pytest.mark.django_db
class TestCompression:
    def test_a_list_response_is_gzipped_for_a_client_that_accepts_it(self, make_authed_client):
        user = UserFactory()
        equb = EqubFactory(creator=user, max_members=20)
        client = make_authed_client(user)

        response = client.get(reverse("equb-list"), HTTP_ACCEPT_ENCODING="gzip")

        assert response.status_code == 200
        assert response["Content-Encoding"] == "gzip"
        assert gzip.decompress(response.content).startswith(b"[")

    def test_the_uncompressed_body_is_still_served_to_a_client_that_does_not_ask(
        self, make_authed_client
    ):
        user = UserFactory()
        EqubFactory(creator=user, max_members=20)
        client = make_authed_client(user)

        response = client.get(reverse("equb-list"), HTTP_ACCEPT_ENCODING="")

        assert response.status_code == 200
        assert "Content-Encoding" not in response

    def test_compression_varies_the_cache_key(self, make_authed_client):
        user = UserFactory()
        EqubFactory(creator=user, max_members=20)
        client = make_authed_client(user)

        response = client.get(reverse("equb-list"), HTTP_ACCEPT_ENCODING="gzip")

        assert "Accept-Encoding" in response.get("Vary", "")


@pytest.mark.django_db
class TestRenderer:
    def test_the_browsable_html_api_is_not_reachable(self, make_authed_client):
        client = make_authed_client()

        response = client.get(reverse("equb-list"), HTTP_ACCEPT="text/html")

        assert response.status_code == 406
