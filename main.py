"""ECS 198F Discord Bot - Main entry point."""

import hashlib
import logging
import os
import sys

import discord

# Initialize Django before any imports that use Django models
import django
from discord.ext import commands

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wccomps.settings")
django.setup()

from bot.discord_queue import DiscordQueueProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class Ecs198fBot(commands.Bot):
    """ECS 198F Discord Bot — authenticates students via Authentik and assigns roles."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.guilds = True

        super().__init__(command_prefix="!", intents=intents)

        self.queue_processor: DiscordQueueProcessor | None = None

    def _get_command_hash(self) -> str:
        """Hash cog source files to detect command changes."""
        from pathlib import Path

        cogs_dir = Path(__file__).parent / "bot" / "cogs"
        hasher = hashlib.sha256()
        for cog_file in sorted(cogs_dir.glob("*.py")):
            hasher.update(cog_file.read_bytes())
        return hasher.hexdigest()[:16]

    async def _should_sync_commands(self) -> bool:
        """Check if commands have changed and need syncing."""
        from asgiref.sync import sync_to_async

        from core.models import BotState

        current_hash = self._get_command_hash()

        # Force sync if explicitly requested
        if os.environ.get("SYNC_COMMANDS", "").lower() in ("true", "1", "yes"):
            logger.info(f"SYNC_COMMANDS=true, forcing sync (hash: {current_hash})")
            await sync_to_async(BotState.objects.update_or_create)(key="command_hash", defaults={"value": current_hash})
            return True

        # Check stored hash
        try:
            stored = await sync_to_async(BotState.objects.get)(key="command_hash")
            if stored.value == current_hash:
                logger.info(f"Commands unchanged (hash: {current_hash}), skipping sync")
                return False
            logger.info(f"Commands changed ({stored.value} -> {current_hash}), will sync")
        except BotState.DoesNotExist:
            logger.info(f"No stored command hash, will sync (hash: {current_hash})")

        await sync_to_async(BotState.objects.update_or_create)(key="command_hash", defaults={"value": current_hash})
        return True

    async def setup_hook(self) -> None:
        """Setup hook called when bot is ready."""
        logger.info("Loading cogs...")

        await self.load_extension("bot.cogs.ecs198f_auth")

        logger.info("Cogs loaded")

        # Register persistent view for ecs198f-auth button
        from bot.cogs.ecs198f_auth import Ecs198fAuthView

        self.add_view(Ecs198fAuthView())
        logger.info("Registered persistent ecs198f auth view")

        # Log registered commands for debugging
        commands_list = self.tree.get_commands()
        logger.info(f"Registered {len(commands_list)} top-level commands:")
        for cmd in commands_list:
            logger.info(f"  - {cmd.name}")

        # Sync slash commands to the configured guild
        from bot.config import DISCORD_GUILD_ID

        if not await self._should_sync_commands():
            return

        if DISCORD_GUILD_ID:
            guild = discord.Object(id=DISCORD_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            try:
                await self.tree.sync(guild=guild)
                logger.info(f"Command tree synced to guild ({DISCORD_GUILD_ID})")
            except discord.HTTPException as e:
                logger.warning(f"Guild sync failed: {e}")

        # Clear global commands to avoid duplicates
        self.tree.clear_commands(guild=None)
        try:
            await self.tree.sync()
            logger.info("Cleared global commands")
        except discord.HTTPException as e:
            logger.warning(f"Failed to clear global commands: {e}")

    async def on_ready(self) -> None:
        """Called when bot is ready."""
        if not self.user:
            logger.error("Bot user is None in on_ready")
            return
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guild(s)")

        for guild in self.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id})")

        # Start task queue processor
        if not self.queue_processor:
            self.queue_processor = DiscordQueueProcessor(self)
            self.queue_processor.start()

    async def close(self) -> None:
        """Cleanup on bot shutdown."""
        logger.info("Shutting down bot...")
        if self.queue_processor:
            self.queue_processor.stop()
        await super().close()


def main() -> None:
    """Main entry point."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        sys.exit(1)

    bot = Ecs198fBot()

    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
