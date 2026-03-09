from django.urls import reverse
from rest_framework import status

import pytest

from .models import User
from .factories import UserFactory


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, api_client):
        data = {
            "username": "new_user",
            "first_name": "New",
            "last_name": "User",
            "email": "new_user@example.com",
            "password": "a-Str0ng-password!",
            "password2": "a-Str0ng-password!",
        }
        response = api_client.post(reverse("user-list"), data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["username"] == "new_user"
        assert User.objects.filter(username="new_user").exists()

    def test_register_duplicate_email_rejected(self, api_client):
        UserFactory(email="taken@example.com")
        data = {
            "username": "someone_else",
            "first_name": "A",
            "last_name": "B",
            "email": "taken@example.com",
            "password": "a-Str0ng-password!",
            "password2": "a-Str0ng-password!",
        }
        response = api_client.post(reverse("user-list"), data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.json()

    def test_register_password_mismatch_rejected(self, api_client):
        data = {
            "username": "mismatch_user",
            "first_name": "A",
            "last_name": "B",
            "email": "mismatch@example.com",
            "password": "a-Str0ng-password!",
            "password2": "different-password!",
        }
        response = api_client.post(reverse("user-list"), data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()


@pytest.mark.django_db
class TestTokenAuth:
    def test_obtain_and_refresh_token(self, api_client):
        UserFactory(username="token_user", password="a-Str0ng-password!")

        response = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "token_user", "password": "a-Str0ng-password!"},
        )
        assert response.status_code == status.HTTP_200_OK
        refresh_token = response.json()["refresh"]

        refresh_response = api_client.post(
            reverse("token_refresh"), {"refresh": refresh_token}
        )
        assert refresh_response.status_code == status.HTTP_200_OK
        assert "access" in refresh_response.json()

    def test_obtain_token_wrong_password_rejected(self, api_client):
        UserFactory(username="token_user_2", password="a-Str0ng-password!")

        response = api_client.post(
            reverse("token_obtain_pair"),
            {"username": "token_user_2", "password": "wrong-password"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestCheckSigninMethod:
    def test_existing_password_user(self, api_client):
        UserFactory(email="pw_user@example.com")
        response = api_client.post(
            reverse("check_signin_method"), {"email": "pw_user@example.com"}
        )
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["exists"] is True
        assert body["has_password"] is True
        assert body["has_google_signin"] is False
        assert body["primary_method"] == "password"

    def test_nonexistent_email(self, api_client):
        response = api_client.post(
            reverse("check_signin_method"), {"email": "nobody@example.com"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["exists"] is False

    def test_missing_email_rejected(self, api_client):
        response = api_client.post(reverse("check_signin_method"), {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestSmartPasswordReset:
    def test_reset_for_password_user_succeeds(self, api_client, mailoutbox):
        user = UserFactory(email="reset_target@example.com")
        response = api_client.post(
            reverse("smart_password_reset"), {"email": user.email}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["signin_method"] == "password"
        assert len(mailoutbox) == 1

