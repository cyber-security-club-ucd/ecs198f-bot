"""Authentik-backed authorization utilities."""

from django.contrib.auth.models import AnonymousUser, User

from .models import UserGroups


def get_authentik_groups(user: User | AnonymousUser) -> list[str]:
    """Return the Authentik groups for *user* (empty list for anonymous users)."""
    if isinstance(user, AnonymousUser):
        return []
    try:
        return list(user.usergroups.groups)
    except UserGroups.DoesNotExist:
        return []


def get_authentik_id(user: User | AnonymousUser) -> str | None:
    """Return the Authentik user UUID (``sub`` claim) for *user*, or ``None``."""
    if isinstance(user, AnonymousUser):
        return None
    try:
        return user.usergroups.authentik_id
    except UserGroups.DoesNotExist:
        return None
