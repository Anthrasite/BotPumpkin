"""A collection of utility functions for performing typing and error checking on discord.ext.commands.Bot objects."""
from typing import Optional

# Third party imports
import discord
from discord.ext import commands


# *** get_owner_if_set ******************************************************

def get_owner_if_set(bot: commands.Bot) -> Optional[discord.User]:
    """Return the owner of the given bot, if it has one.

    Args:
        bot (commands.Bot): The bot to return the owner of.

    Returns:
        Optional[discord.User]: The owner of the bot, or None if the bot has no owner.
    """
    owner_id: Optional[int] = bot.owner_id
    if owner_id is None:
        return None
    return bot.get_user(owner_id)


# *** get_guild *************************************************************

def get_guild(bot: commands.Bot, guild_id: int) -> discord.Guild:
    """Return the guild with the given id from the given bot.

    Args:
        bot (commands.Bot): The bot to return the guild from.
        guild_id (int): The id of the guild.

    Returns:
        discord.Guild: The guild with the given id.
    """
    guild: Optional[discord.Guild] = bot.get_guild(guild_id)
    if guild is None:
        raise ValueError("Bot not in guild")
    return guild
