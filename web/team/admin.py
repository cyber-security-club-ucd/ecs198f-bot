"""Django admin configuration for team app (auth tokens)."""

from django.contrib import admin

from .models import LinkRateLimit, LinkToken


@admin.register(LinkToken)
class LinkTokenAdmin(admin.ModelAdmin[LinkToken]):
    list_display = ["token", "discord_username", "used", "expires_at", "created_at"]
    list_filter = ["used"]
    search_fields = ["discord_username", "token"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(LinkRateLimit)
class LinkRateLimitAdmin(admin.ModelAdmin[LinkRateLimit]):
    list_display = ["discord_id", "attempted_at"]
    list_filter = ["attempted_at"]
    search_fields = ["discord_id"]
    readonly_fields = ["attempted_at"]
    ordering = ["-attempted_at"]
