"""Database models for ECS 198F Discord authentication."""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserGroups(models.Model):
    """Stores Authentik groups for a user.  Refreshed on every OAuth login."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    authentik_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Authentik user UUID (sub claim)",
    )
    groups = models.JSONField(
        default=list,
        help_text="List of Authentik group names",
    )

    class Meta:
        verbose_name = "User Groups"
        verbose_name_plural = "User Groups"

    def __str__(self) -> str:
        return f"{self.user.username} ({len(self.groups)} groups)"


class DiscordTask(models.Model):
    """Task queue for Discord API operations (rate-limit resilience).

    Supported task types:
        assign_group_roles: {"discord_id": int, "authentik_groups": list[str]}
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    TASK_TYPE_CHOICES = [
        ("assign_group_roles", "Assign Group-Based Roles"),
    ]

    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
            models.Index(fields=["task_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_type} ({self.status})"

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        required_keys = {
            "assign_group_roles": {"discord_id", "authentik_groups"},
        }
        if self.task_type in required_keys:
            missing = required_keys[self.task_type] - set(self.payload.keys())
            if missing:
                raise ValidationError(f"Payload for {self.task_type} missing keys: {missing}")

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.pk:
            self.clean()
        super().save(*args, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def create_assign_group_roles(cls, discord_id: int, authentik_groups: list[str]) -> "DiscordTask":
        """Create a task to assign group-based roles to a Discord user."""
        return cls.objects.create(
            task_type="assign_group_roles",
            payload={"discord_id": discord_id, "authentik_groups": authentik_groups},
            status="pending",
        )


class BotState(models.Model):
    """Persistent key-value store for bot state (e.g. command hash)."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"
