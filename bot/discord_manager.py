"""Discord role management for ECS 198F authentication."""

import logging

import discord
from django.conf import settings

logger = logging.getLogger(__name__)


class DiscordManager:
    """Manages Discord role assignment for authenticated students."""

    def __init__(self, guild: discord.Guild) -> None:
        self.guild = guild

    async def assign_group_roles(self, member: discord.Member, authentik_groups: list[str]) -> bool:
        """Assign Discord roles based on Authentik group membership.

        Iterates over GROUP_ROLE_MAPPING and assigns any role whose corresponding
        Authentik group is present in *authentik_groups*.

        Returns True on success, False if the bot lacks permission.
        """
        roles_to_add = []

        for group_name, role_id in settings.GROUP_ROLE_MAPPING.items():
            if group_name in authentik_groups:
                role = self.guild.get_role(role_id)
                if role:
                    roles_to_add.append(role)
                else:
                    logger.warning(f"Role {role_id} for group '{group_name}' not found in guild")

        if not roles_to_add:
            logger.info(f"No roles to assign for {member} (groups: {authentik_groups})")
            return True

        try:
            await member.add_roles(*roles_to_add, reason="ECS 198F Authentik group assignment")
            logger.info(f"Assigned [{', '.join(r.name for r in roles_to_add)}] to {member}")
            return True
        except discord.errors.Forbidden:
            logger.exception(f"No permission to assign roles to {member}")
            return False
        except Exception as e:
            logger.exception(f"Error assigning group roles to {member}: {e}")
            return False
