"""Middleware for ECS 198F Discord authentication bot."""

import logging
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Add security headers to all responses."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' "
                "https://unpkg.com https://static.cloudflareinsights.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "base-uri 'self'"
            )
        return response


class AuthentikRequiredMiddleware:
    """Require Authentik login for all pages except the OAuth flow and the 198F token routes."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

        self.whitelist_prefixes = ["/static/"]
        self.whitelist_exact = [
            "/health/",
            "/auth/login/",
            "/auth/callback/",
            "/auth/logout/",
            "/auth/198f",   # token-based — unauthenticated users start the flow here
        ]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        for prefix in self.whitelist_prefixes:
            if request.path.startswith(prefix):
                return self.get_response(request)
        if request.path in self.whitelist_exact:
            return self.get_response(request)

        if not request.user.is_authenticated:
            next_url = request.path
            if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                next_url = "/"
            safe_next = quote(next_url, safe="")
            return redirect(f"/auth/login/?next={safe_next}")

        return self.get_response(request)


class QueryTracker:
    """Tracks database queries during a request."""

    def __init__(self) -> None:
        self.queries: list[float] = []

    def __call__(  # type: ignore[explicit-any]
        self,
        execute: Callable[[str, Any, bool, dict[str, Any]], Any],
        sql: str,
        params: Any,
        many: bool,
        context: dict[str, Any],
    ) -> Any:
        start = time.time()
        result = execute(sql, params, many, context)
        self.queries.append((time.time() - start) * 1000)
        return result


class AccessLoggingMiddleware:
    """Log all requests with username, status, and query metrics."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/static/"):
            return self.get_response(request)

        start_time = time.time()
        tracker = QueryTracker()

        with connection.execute_wrapper(tracker):
            response = self.get_response(request)

        duration_ms = (time.time() - start_time) * 1000
        username = request.user.username if request.user.is_authenticated else "-"
        logger.info(
            '%s - - "%s %s" %d %.0fms [%dq %.0fms]',
            request.META.get("REMOTE_ADDR", "-"),
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            len(tracker.queries),
            sum(tracker.queries),
        )
        return response
