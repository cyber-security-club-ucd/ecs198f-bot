"""Tests for the ECS 198F authentication views."""

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from team.models import LinkToken

pytestmark = pytest.mark.django_db

ECS198F_DISCORD_ID = 9876543210
ECS198F_DISCORD_USERNAME = "student#0001"


@pytest.fixture
def valid_198f_token():
    """Create a fresh, unused LinkToken for the 198F flow."""
    return LinkToken.objects.create(
        token="test198ftoken1234567890abcdef",
        discord_id=ECS198F_DISCORD_ID,
        discord_username=ECS198F_DISCORD_USERNAME,
        expires_at=timezone.now() + timedelta(minutes=15),
    )


@pytest.fixture
def expired_198f_token():
    """Create an expired LinkToken."""
    return LinkToken.objects.create(
        token="expiredtoken1234567890abcdef",
        discord_id=ECS198F_DISCORD_ID,
        discord_username=ECS198F_DISCORD_USERNAME,
        expires_at=timezone.now() - timedelta(minutes=1),
    )


class TestAuth198fInitiate:
    """Tests for auth_198f_initiate view."""

    def test_missing_token_returns_400(self):
        client = Client()
        response = client.get(reverse("auth_198f_initiate"))
        assert response.status_code == 400

    def test_invalid_token_renders_error(self):
        client = Client()
        response = client.get(reverse("auth_198f_initiate") + "?token=nonexistent")
        assert response.status_code == 200
        assert b"expired or is invalid" in response.content

    def test_expired_token_renders_error(self, expired_198f_token):
        client = Client()
        url = reverse("auth_198f_initiate") + f"?token={expired_198f_token.token}"
        response = client.get(url)
        assert response.status_code == 200
        assert b"expired" in response.content.lower()

    def test_valid_token_redirects_to_oauth(self, valid_198f_token):
        client = Client()
        url = reverse("auth_198f_initiate") + f"?token={valid_198f_token.token}"
        response = client.get(url)
        assert response.status_code == 302
        assert "/auth/login/" in response["Location"]
        assert "198f-callback" in response["Location"]


class TestAuth198fCallback:
    """Tests for auth_198f_callback view."""

    def test_unauthenticated_user_redirected(self, valid_198f_token):
        """Unauthenticated users should be redirected to login."""
        client = Client()
        url = reverse("auth_198f_callback") + f"?token={valid_198f_token.token}"
        response = client.get(url)
        # Django login_required or the view itself will redirect
        assert response.status_code in (302, 403)

    def test_user_without_198f_group_sees_error(self, valid_198f_token, create_user_with_groups):
        """Users without 198F-student group should see an access denied error."""
        user = create_user_with_groups("nonstudent", ["some-other-group"])
        client = Client()
        client.force_login(user)

        session = client.session
        session["pending_198f_token"] = valid_198f_token.token
        session.save()

        url = reverse("auth_198f_callback") + f"?token={valid_198f_token.token}"
        response = client.get(url)
        assert response.status_code == 200
        assert b"Access denied" in response.content or b"does not have the required" in response.content

    def test_user_with_198f_group_sees_success(self, valid_198f_token, create_user_with_groups):
        """Users with the 198F-student group should see the success page."""
        from core.models import DiscordTask

        user = create_user_with_groups("student01", ["198F-student"])
        client = Client()
        client.force_login(user)

        session = client.session
        session["pending_198f_token"] = valid_198f_token.token
        session.save()

        url = reverse("auth_198f_callback") + f"?token={valid_198f_token.token}"
        response = client.get(url)
        assert response.status_code == 200
        assert b"Authentication Successful" in response.content

        # Token should be marked used
        valid_198f_token.refresh_from_db()
        assert valid_198f_token.used is True

        # A Discord task should have been queued
        task = DiscordTask.objects.filter(task_type="assign_group_roles").first()
        assert task is not None
        assert task.payload["discord_id"] == ECS198F_DISCORD_ID
        assert "198F-student" in task.payload["authentik_groups"]
