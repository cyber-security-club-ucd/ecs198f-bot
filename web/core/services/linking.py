"""Token validation for the ECS 198F Discord authentication flow."""

import logging
from dataclasses import dataclass

from team.models import LinkToken

logger = logging.getLogger(__name__)


@dataclass
class LinkResult:
    """Represents a validation failure with an error page and context."""

    success: bool
    error_template: str | None = None
    error_context: dict[str, str] | None = None


def validate_link_token(url_token: str | None, session_token: str | None, username: str) -> LinkResult | LinkToken:
    """Validate the one-time auth token from the URL query parameter.

    Returns a ``LinkToken`` on success, or a ``LinkResult`` with error details
    on failure.

    The *session_token* is compared to *url_token* as a CSRF defence; a mismatch
    is logged as a warning but the flow continues (the session may have cycled
    during OAuth).
    """
    if not url_token:
        return LinkResult(
            success=False,
            error_template="link_error.html",
            error_context={
                "error": "Invalid request",
                "message": "Missing authentication token. Please click the Authenticate button again.",
            },
        )

    if session_token and session_token != url_token:
        logger.warning(
            f"Session token mismatch for {username}: "
            f"session='{session_token[:8]}...' != url='{url_token[:8]}...'"
        )
        return LinkResult(
            success=False,
            error_template="link_error.html",
            error_context={
                "error": "Security verification failed",
                "message": "The request could not be verified. Please click the Authenticate button again.",
            },
        )

    if not session_token:
        logger.info(f"Session token not found (likely cycled during OAuth) for user {username}")

    try:
        link_token = LinkToken.objects.get(token=url_token, used=False)
    except LinkToken.DoesNotExist:
        return LinkResult(
            success=False,
            error_template="link_error.html",
            error_context={
                "error": "Invalid or expired token",
                "message": "This link has expired or been used. Please click the Authenticate button again.",
            },
        )

    if link_token.is_expired():
        return LinkResult(
            success=False,
            error_template="link_error.html",
            error_context={
                "error": "Token expired",
                "message": "This link has expired (15-minute limit). Please click the Authenticate button again.",
            },
        )

    return link_token
