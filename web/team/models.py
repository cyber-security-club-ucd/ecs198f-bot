"""Token models for the ECS 198F Discord authentication flow."""

from django.db import models
from django.utils import timezone


class LinkToken(models.Model):
    """One-time token generated when a student clicks the Discord auth button."""

    token = models.CharField(max_length=64, unique=True)
    discord_id = models.BigIntegerField()
    discord_username = models.CharField(max_length=255)
    used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["token", "used", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Token for {self.discord_username}"

    def is_expired(self) -> bool:
        """Return True if the token has passed its expiry time."""
        return timezone.now() > self.expires_at


class LinkRateLimit(models.Model):
    """Rate-limiting record — one row per auth attempt per Discord user."""

    discord_id = models.BigIntegerField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["discord_id", "-attempted_at"]),
        ]

    def __str__(self) -> str:
        return f"Auth attempt by {self.discord_id} at {self.attempted_at}"
