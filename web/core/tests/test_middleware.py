"""Tests for middleware (SecurityHeadersMiddleware, AuthentikRequiredMiddleware)."""

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import Client, RequestFactory

from core.middleware import AuthentikRequiredMiddleware, SecurityHeadersMiddleware

pytestmark = pytest.mark.django_db


@pytest.fixture
def get_response():
    def _get_response(request):
        return HttpResponse("OK")
    return _get_response


@pytest.fixture
def authed_middleware(get_response):
    return AuthentikRequiredMiddleware(get_response)


@pytest.fixture
def authed_user(create_user_with_groups):
    return create_user_with_groups("testuser", ["198F-student"])


class TestMiddlewareConfiguration:
    def test_authentik_middleware_runs_after_auth_middleware(self):
        middleware_list = list(settings.MIDDLEWARE)
        auth_idx = middleware_list.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        authentik_idx = middleware_list.index("core.middleware.AuthentikRequiredMiddleware")
        assert authentik_idx > auth_idx


class TestAuthentikRequiredMiddleware:
    def test_authenticated_user_passes_through(self, authed_middleware, authed_user):
        factory = RequestFactory()
        request = factory.get("/auth/198f-callback")
        request.user = authed_user
        response = authed_middleware(request)
        assert response.status_code == 200

    def test_anonymous_user_redirected_to_login(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/some/protected/path/")
        request.user = AnonymousUser()
        response = authed_middleware(request)
        assert response.status_code == 302
        assert "/auth/login/" in response.url

    def test_redirect_includes_next_url(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/some/protected/path/")
        request.user = AnonymousUser()
        response = authed_middleware(request)
        assert "next=" in response.url

    def test_health_path_whitelisted(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/health/")
        request.user = AnonymousUser()
        assert authed_middleware(request).status_code == 200

    def test_static_path_whitelisted(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/static/css/style.css")
        request.user = AnonymousUser()
        assert authed_middleware(request).status_code == 200

    def test_auth_login_whitelisted(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/auth/login/")
        request.user = AnonymousUser()
        assert authed_middleware(request).status_code == 200

    def test_auth_callback_whitelisted(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/auth/callback/")
        request.user = AnonymousUser()
        assert authed_middleware(request).status_code == 200

    def test_auth_logout_whitelisted(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("/auth/logout/")
        request.user = AnonymousUser()
        assert authed_middleware(request).status_code == 200

    def test_auth_198f_whitelisted(self, authed_middleware):
        """The 198F token initiation path must be publicly accessible."""
        factory = RequestFactory()
        request = factory.get("/auth/198f")
        request.user = AnonymousUser()
        assert authed_middleware(request).status_code == 200

    def test_next_url_sanitization_rejects_external_url(self, authed_middleware):
        factory = RequestFactory()
        request = factory.get("//evil.com/steal")
        request.user = AnonymousUser()
        response = authed_middleware(request)
        assert response.status_code == 302
        assert "evil.com" not in response.url or "%2F" in response.url

    @pytest.mark.parametrize("path", ["/", "/some/page/", "/auth/198f-callback"])
    def test_protected_paths_require_auth(self, authed_middleware, path):
        factory = RequestFactory()
        request = factory.get(path)
        request.user = AnonymousUser()
        response = authed_middleware(request)
        assert response.status_code == 302
        assert "/auth/login/" in response.url


class TestSecurityHeadersMiddleware:
    def test_csp_header_is_present(self):
        client = Client()
        response = client.get("/health/")
        assert "Content-Security-Policy" in response

    def test_csp_restricts_scripts(self):
        client = Client()
        response = client.get("/health/")
        assert "script-src" in response["Content-Security-Policy"]

    def test_csp_disallows_unsafe_eval(self):
        client = Client()
        response = client.get("/health/")
        assert "'unsafe-eval'" not in response["Content-Security-Policy"]


class TestSecuritySettings:
    def test_allowed_hosts_not_wildcard(self):
        assert "*" not in settings.ALLOWED_HOSTS

    def test_csrf_trusted_origins_https_only(self):
        http_origins = [o for o in settings.CSRF_TRUSTED_ORIGINS if o.startswith("http://")]
        assert http_origins == []

    def test_session_cookie_httponly(self):
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_authentik_url_points_to_daviscybersec(self):
        """Authentik auth URL must point to auth.daviscybersec.org."""
        from urllib.parse import urlparse

        parsed = urlparse(settings.AUTHENTIK_URL)
        assert parsed.hostname in ("auth.daviscybersec.org", "daviscybersec.org")
