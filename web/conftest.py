"""Shared pytest fixtures for all web tests."""

import os
import socket
from collections.abc import Callable
from typing import Any

import pytest
from django.contrib.auth.models import User
from django.test import Client


def pytest_configure(config: pytest.Config) -> None:
    """Fail fast if the test database is not reachable."""
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "5433"))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
    except OSError as err:
        raise pytest.UsageError(
            f"Test database not reachable at {host}:{port}. Run: docker compose -f docker-compose.test.yml up -d --wait"
        ) from err
    finally:
        sock.close()


from core.models import UserGroups


@pytest.fixture
def create_user_with_groups(db: Any) -> Callable[..., User]:
    """Factory fixture: create a Django user with Authentik groups."""

    def _create(username: str, groups: list[str]) -> User:
        user = User.objects.create_user(username=username, password="testpass123")
        UserGroups.objects.create(
            user=user,
            authentik_id=f"{username}-uid",
            groups=groups,
        )
        return user

    return _create


@pytest.fixture
def unauthenticated_client() -> Client:
    """Return an unauthenticated Django test client."""
    return Client()
