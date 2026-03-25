"""ECS 198F course authentication cog.

Posts a persistent "Authenticate" button to the configured ecs198f-auth
channel.  When a student clicks the button, they receive an ephemeral
message with a one-time OAuth link.  After authenticating via Authentik
and being verified as a member of the "198F-student" group, the bot
automatically assigns them the ecs198f-student Discord role.
"""

import logging
import secrets
from datetime import timedelta

import discord
from discord.ext import commands
from django.conf import settings
from django.utils import timezone

from bot.config import ECS198F_AUTH_CHANNEL_ID
from team.models import LinkRateLimit, LinkToken

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_HOURS = 1
TOKEN_EXPIRY_MINUTES = 15

# Custom ID used to re-attach the view on bot restart (persistent view).
AUTH_BUTTON_CUSTOM_ID = "ecs198f_auth_button"


async def _check_rate_limit(discord_id: int) -> tuple[bool, int]:
    """Return (is_allowed, attempt_count) for the past hour."""
    one_hour_ago = timezone.now() - timedelta(hours=RATE_LIMIT_WINDOW_HOURS)
    count = await LinkRateLimit.objects.filter(
        discord_id=discord_id, attempted_at__gte=one_hour_ago
    ).acount()
    return count < RATE_LIMIT_MAX, count


async def _create_auth_token(discord_id: int, discord_username: str) -> str:
    """Create a LinkToken and return the full auth URL."""
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
    await LinkToken.objects.acreate(
        token=token,
        discord_id=discord_id,
        discord_username=discord_username,
        expires_at=expires_at,
    )
    return f"{settings.BASE_URL}/auth/198f?token={token}"


class Ecs198fAuthView(discord.ui.View):
    """Persistent view containing the authentication button."""

    def __init__(self) -> None:
        # timeout=None makes this view persist across bot restarts
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Authenticate",
        style=discord.ButtonStyle.primary,
        emoji="🔐",
        custom_id=AUTH_BUTTON_CUSTOM_ID,
    )
    async def on_authenticate_button_click(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Handle button click: generate a token and reply with the auth URL."""
        user = interaction.user
        discord_id = user.id

        is_allowed, attempt_count = await _check_rate_limit(discord_id)
        if not is_allowed:
            await interaction.response.send_message(
                f"⚠️ Rate limit exceeded. You have made {attempt_count} attempts in the last hour. "
                f"Please wait before trying again (limit: {RATE_LIMIT_MAX} per hour).",
                ephemeral=True,
            )
            return

        await LinkRateLimit.objects.acreate(discord_id=discord_id)

        auth_url = await _create_auth_token(discord_id, str(user))

        embed = discord.Embed(
            title="ECS 198F Authentication",
            description=(
                "Click the link below to authenticate with your ECS 198F Authentik account.\n\n"
                f"[**Click here to authenticate**]({auth_url})\n\n"
                f"⏱️ This link expires in **{TOKEN_EXPIRY_MINUTES} minutes**.\n"
                "You will be redirected to Authentik to log in. "
                "After successful login, you will automatically receive the **ecs198f-student** role."
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="Only you can see this message.")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Generated 198F auth token for {user} ({discord_id})")


class Ecs198fAuthCog(commands.Cog):
    """Manages the ECS 198F authentication panel."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Post (or refresh) the auth panel in the ecs198f-auth channel."""
        if not ECS198F_AUTH_CHANNEL_ID:
            logger.info("ECS198F_AUTH_CHANNEL_ID not set, skipping auth panel")
            return

        channel = self.bot.get_channel(ECS198F_AUTH_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(ECS198F_AUTH_CHANNEL_ID)
            except discord.NotFound:
                logger.warning(f"ecs198f-auth channel {ECS198F_AUTH_CHANNEL_ID} not found")
                return
            except discord.Forbidden:
                logger.warning(f"No access to ecs198f-auth channel {ECS198F_AUTH_CHANNEL_ID}")
                return

        if not isinstance(channel, discord.TextChannel):
            logger.warning(f"Channel {ECS198F_AUTH_CHANNEL_ID} is not a text channel")
            return

        embed = discord.Embed(
            title="ECS 198F — Student Authentication",
            description=(
                "Welcome to ECS 198F!\n\n"
                "Click the **Authenticate** button below to verify your student status "
                "and receive access to the course channels."
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="How it works",
            value=(
                "1. Click **Authenticate**\n"
                "2. Log in with your ECS 198F Authentik credentials\n"
                "3. Your **ecs198f-student** role will be assigned automatically"
            ),
            inline=False,
        )

        view = Ecs198fAuthView()

        # Look for an existing panel posted by this bot so we can edit it
        # instead of spamming the channel on every restart.
        existing_message = None
        try:
            async for message in channel.history(limit=50, oldest_first=True):
                if (
                    message.author == self.bot.user
                    and message.embeds
                    and message.embeds[0].title == embed.title
                ):
                    existing_message = message
                    break
        except discord.Forbidden:
            logger.warning(f"Cannot read history of ecs198f-auth channel {ECS198F_AUTH_CHANNEL_ID}")

        try:
            if existing_message:
                await existing_message.edit(embed=embed, view=view)
                logger.info("Refreshed existing ecs198f-auth panel")
            else:
                await channel.send(embed=embed, view=view)
                logger.info(f"Posted ecs198f-auth panel to channel {ECS198F_AUTH_CHANNEL_ID}")
        except discord.Forbidden:
            logger.warning(f"No permission to post to ecs198f-auth channel {ECS198F_AUTH_CHANNEL_ID}")
        except Exception as e:
            logger.exception(f"Error posting ecs198f-auth panel: {e}")


async def setup(bot: commands.Bot) -> None:
    """Add the cog to the bot."""
    await bot.add_cog(Ecs198fAuthCog(bot))
