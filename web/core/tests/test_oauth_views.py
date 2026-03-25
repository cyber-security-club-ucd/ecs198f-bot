"""Tests for OAuth views (login / callback / logout)."""

from unittest.mock import patch

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestOAuthLogin:
    def test_login_without_client_id_returns_500(self):
        """Missing AUTHENTIK_CLIENT_ID should return a 500 error page."""
        client = Client()
        with patch("core.oauth._get_oauth_config") as mock_cfg:
            mock_cfg.return_value = {
                "client_id": "",
                "client_secret": "",
                "authorization_endpoint": "https://auth.daviscybersec.org/authorize/",
                "token_endpoint": "https://auth.daviscybersec.org/token/",
                "userinfo_endpoint": "https://auth.daviscybersec.org/userinfo/",
                "end_session_endpoint": "https://auth.daviscybersec.org/end-session/",
            }
            response = client.get("/auth/login/")
        assert response.status_code == 500

    def test_login_redirects_to_authentik(self):
        """Login should redirect to the Authentik authorization endpoint."""
        client = Client()
        with patch("core.oauth._get_oauth_config") as mock_cfg:
            mock_cfg.return_value = {
                "client_id": "test-client-id",
                "client_secret": "test-secret",
                "authorization_endpoint": "https://auth.daviscybersec.org/application/o/authorize/",
                "token_endpoint": "https://auth.daviscybersec.org/application/o/token/",
                "userinfo_endpoint": "https://auth.daviscybersec.org/application/o/userinfo/",
                "end_session_endpoint": "https://auth.daviscybersec.org/application/o/discord-bot/end-session/",
            }
            response = client.get("/auth/login/")
        assert response.status_code == 302
        assert "daviscybersec.org" in response.url
        assert "client_id=test-client-id" in response.url


class TestOAuthCallback:
    def test_callback_rejects_missing_state(self):
        client = Client()
        response = client.get("/auth/callback/?code=testcode")
        assert response.status_code == 200
        assert b"Session Expired" in response.content

    def test_callback_handles_access_denied(self):
        client = Client()
        response = client.get("/auth/callback/?error=access_denied")
        assert response.status_code == 200
        assert b"Login Cancelled" in response.content

    def test_callback_rejects_bad_state_signature(self):
        client = Client()
        response = client.get("/auth/callback/?code=testcode&state=tampered_state")
        assert response.status_code == 200
        assert b"Security Error" in response.content


class TestOAuthLogout:
    def test_logout_clears_session_and_redirects(self):
        """Logout should clear the Django session and redirect to Authentik."""
        client = Client()
        with patch("core.oauth._get_oauth_config") as mock_cfg:
            mock_cfg.return_value = {
                "client_id": "test-client-id",
                "client_secret": "test-secret",
                "authorization_endpoint": "https://auth.daviscybersec.org/application/o/authorize/",
                "token_endpoint": "https://auth.daviscybersec.org/application/o/token/",
                "userinfo_endpoint": "https://auth.daviscybersec.org/application/o/userinfo/",
                "end_session_endpoint": "https://auth.daviscybersec.org/application/o/discord-bot/end-session/",
            }
            response = client.get("/auth/logout/")
        assert response.status_code == 302
        assert "daviscybersec.org" in response.url
