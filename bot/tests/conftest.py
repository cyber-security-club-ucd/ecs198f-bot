"""Pytest fixtures for bot tests."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
import pytest_asyncio
from django.contrib.auth.models import User

from core.models import UserGroups


@pytest.fixture
def mock_interaction() -> Any:
    """Create a mock Discord interaction."""
    interaction = AsyncMock(spec=discord.Interaction)

    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 211533935144992768
    interaction.user.name = "testuser"
    interaction.user.__str__ = MagicMock(return_value="testuser#0001")
    interaction.user.mention = "<@211533935144992768>"

    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 525435725123158026
    interaction.guild.name = "Test Guild"

    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()

    return interaction


@pytest.fixture
def mock_bot() -> Any:
    """Create a mock Discord bot."""
    bot = AsyncMock(spec=discord.Client)
    bot.user = MagicMock()
    bot.user.id = 1422808875651829785
    bot.user.name = "ecs198f-bot"

    bot.tree = MagicMock()
    bot.tree.get_commands = MagicMock(return_value=[])
    bot.tree.add_command = MagicMock()

    return bot


@pytest.fixture
def mock_discord_guild() -> Any:
    """Create a mock Discord guild with a student role."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 525435725123158026
    guild.name = "Test Guild"

    student_role = MagicMock(spec=discord.Role)
    student_role.id = 99999999
    student_role.name = "ecs198f-student"

    def get_role_by_id(role_id: int) -> Any:
        return {99999999: student_role}.get(role_id)

    guild.get_role = MagicMock(side_effect=get_role_by_id)
    guild.roles = [student_role]

    return guild


@pytest_asyncio.fixture
async def student_user(db: Any) -> User:
    """Create a Django user with the 198F-student Authentik group."""
    import uuid
    unique_id = str(uuid.uuid4())[:8]
    user = await User.objects.acreate(
        username=f"student_{unique_id}",
        email=f"student_{unique_id}@example.com",
    )
    await UserGroups.objects.acreate(
        user=user,
        authentik_id=f"test-uid-{unique_id}",
        groups=["198F-student"],
    )
    return user


@pytest.fixture(autouse=True)
def _patch_group_role_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch GROUP_ROLE_MAPPING with a non-zero role ID for bot tests."""
    from django.conf import settings

    monkeypatch.setattr(settings, "GROUP_ROLE_MAPPING", {"198F-student": 99999999})
