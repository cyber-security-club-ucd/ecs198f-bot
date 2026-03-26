"""Discord task queue processor — handles assign_group_roles tasks."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta

import discord
from asgiref.sync import sync_to_async
from django.db.models import Q
from django.utils import timezone

from bot.discord_manager import DiscordManager
from core.models import DiscordTask

logger = logging.getLogger(__name__)


class DiscordQueueProcessor:
    """Process Discord tasks from the database queue."""

    QUEUE_POLL_INTERVAL_SECONDS = 2
    QUEUE_BATCH_SIZE = 10
    MAX_BACKOFF_SECONDS = 300

    # Handler registry: task_type -> handler method
    _task_handlers: dict[str, Callable[["DiscordQueueProcessor", DiscordTask], Awaitable[None]]] = {}

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.discord_manager: DiscordManager | None = None
        self.running = False
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start the queue processing loop."""
        self.running = True
        self.task = asyncio.create_task(self._process_loop())
        logger.info("Discord queue processor started")

    def stop(self) -> None:
        """Stop the queue processing loop."""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("Discord queue processor stopped")

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self.running:
            try:
                await self._process_pending_tasks()
            except Exception as e:
                logger.exception(f"Error in queue processor loop: {e}")
            await asyncio.sleep(self.QUEUE_POLL_INTERVAL_SECONDS)

    async def _process_pending_tasks(self) -> None:
        """Fetch and process pending tasks."""

        def get_pending_tasks() -> list[DiscordTask]:
            now = timezone.now()
            return list(
                DiscordTask.objects.filter(
                    Q(status="pending") | Q(status="processing"),
                    Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=now),
                ).order_by("created_at")[: self.QUEUE_BATCH_SIZE]
            )

        tasks = await sync_to_async(get_pending_tasks)()

        # Initialise DiscordManager on first use (guild may not be available at startup)
        if tasks and not self.discord_manager:
            from bot.config import DISCORD_GUILD_ID

            guild = self.bot.get_guild(DISCORD_GUILD_ID)
            if guild:
                self.discord_manager = DiscordManager(guild)
            else:
                logger.warning("Guild not yet available, deferring task processing")
                return

        for task in tasks:
            await self._process_task(task)

    async def _process_task(self, task: DiscordTask) -> None:
        """Process a single task."""

        def mark_processing() -> None:
            task.status = "processing"
            task.save(update_fields=["status"])

        await sync_to_async(mark_processing)()

        try:
            handler = self._task_handlers.get(task.task_type)
            if not handler:
                logger.warning(f"Unknown task type: {task.task_type}")

                def mark_unknown() -> None:
                    task.status = "failed"
                    task.error_message = f"Unknown task type: {task.task_type}"
                    task.save(update_fields=["status", "error_message"])

                await sync_to_async(mark_unknown)()
                return

            await handler(self, task)

            def mark_completed() -> None:
                task.status = "completed"
                task.completed_at = timezone.now()
                task.save(update_fields=["status", "completed_at"])

            await sync_to_async(mark_completed)()
            logger.info(f"Completed task {task.id}: {task.task_type}")

        except discord.errors.RateLimited as e:
            retry_after = e.retry_after

            def handle_rate_limit() -> None:
                task.status = "pending"
                task.next_retry_at = timezone.now() + timedelta(seconds=retry_after + 1)
                task.save(update_fields=["status", "next_retry_at"])

            await sync_to_async(handle_rate_limit)()
            logger.warning(f"Rate limited on task {task.id}, retrying in {retry_after}s")

        except Exception as exc:
            error_msg = str(exc)

            def handle_error() -> tuple[str, int]:
                task.retry_count += 1
                if task.retry_count >= task.max_retries:
                    task.status = "failed"
                    task.error_message = error_msg
                    task.save(update_fields=["status", "retry_count", "error_message"])
                    return "failed", task.retry_count
                backoff = min(2 ** task.retry_count * 5, self.MAX_BACKOFF_SECONDS)
                task.status = "pending"
                task.next_retry_at = timezone.now() + timedelta(seconds=backoff)
                task.error_message = error_msg
                task.save(update_fields=["status", "retry_count", "next_retry_at", "error_message"])
                return "retrying", task.retry_count

            status, count = await sync_to_async(handle_error)()
            if status == "failed":
                logger.error(f"Task {task.id} ({task.task_type}) failed after {count} retries: {error_msg}")
            else:
                logger.warning(f"Task {task.id} ({task.task_type}) failed (attempt {count}): {error_msg}")

    async def _handle_assign_group_roles(self, task: DiscordTask) -> None:
        """Assign Discord roles based on Authentik groups."""
        if not self.discord_manager:
            raise RuntimeError("Discord manager not initialized")

        discord_id = task.payload.get("discord_id")
        authentik_groups = task.payload.get("authentik_groups", [])

        if not discord_id:
            raise ValueError("Missing discord_id in payload")

        guild = self.discord_manager.guild
        member = guild.get_member(discord_id)

        if not member:
            try:
                member = await guild.fetch_member(discord_id)
            except discord.NotFound:
                logger.warning(f"Member {discord_id} not found in guild, skipping group role assignment")
                return
            except Exception as e:
                logger.exception(f"Failed to fetch member {discord_id}: {e}")
                raise

        success = await self.discord_manager.assign_group_roles(member, authentik_groups)
        if not success:
            raise RuntimeError(f"Failed to assign group roles to {member}")

        logger.info(f"Assigned group roles to {member}")


# Register handlers
DiscordQueueProcessor._task_handlers["assign_group_roles"] = DiscordQueueProcessor._handle_assign_group_roles
