"""Django admin configuration for ECS 198F bot."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone

from .models import BotState, DiscordTask, UserGroups


@admin.register(DiscordTask)
class DiscordTaskAdmin(admin.ModelAdmin[DiscordTask]):
    list_display = ["task_type", "status", "retry_count", "created_at", "completed_at"]
    list_filter = ["status", "task_type"]
    search_fields = ["task_type", "error_message"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "completed_at"]

    actions = ["retry_failed_tasks"]

    @admin.action(description="Retry failed tasks")
    def retry_failed_tasks(self, request: HttpRequest, queryset: QuerySet[DiscordTask]) -> None:
        updated = queryset.filter(status="failed").update(
            status="pending",
            retry_count=0,
            next_retry_at=timezone.now(),
            error_message="",
        )
        self.message_user(request, f"{updated} task(s) reset for retry")


@admin.register(BotState)
class BotStateAdmin(admin.ModelAdmin[BotState]):
    list_display = ["key", "value", "updated_at"]
    search_fields = ["key", "value"]
    ordering = ["key"]
    readonly_fields = ["key", "value", "updated_at"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: BotState | None = None) -> bool:
        return False


@admin.register(UserGroups)
class UserGroupsAdmin(admin.ModelAdmin[UserGroups]):
    list_display = ["user", "authentik_id", "group_count"]
    search_fields = ["user__username", "authentik_id"]
    readonly_fields = ["user", "authentik_id", "groups"]

    @admin.display(description="Groups")
    def group_count(self, obj: UserGroups) -> str:
        return str(len(obj.groups))

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: UserGroups | None = None) -> bool:
        return True
