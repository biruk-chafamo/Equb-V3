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

