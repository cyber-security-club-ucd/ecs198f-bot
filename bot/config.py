"""Bot configuration — single source of truth for bot-side environment variables."""

import os

DISCORD_GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", "0"))

# ECS 198F course authentication
ECS198F_AUTH_CHANNEL_ID = int(os.environ.get("ECS198F_AUTH_CHANNEL_ID", "0"))
